use crate::config::Export as _;
use crate::config::{Committee, ConfigError, Parameters, Secret};
use consensus::{Block, Consensus};
use crypto::{SignatureService, Hash};
use log::info;
use mempool::Mempool;
use store::Store;
use tokio::sync::mpsc::{channel, Receiver};
use std::net::SocketAddr;
use std::collections::HashMap;

/// The default channel capacity for this module.
pub const CHANNEL_CAPACITY: usize = 1_000;

pub struct Node {
    pub commit: Receiver<Block>,
}

impl Node {
    pub async fn new(
        committee_file: &str,
        key_file: &str,
        store_path: &str,
        parameters: Option<String>,
    ) -> Result<Self, ConfigError> {
        let (tx_commit, rx_commit) = channel(CHANNEL_CAPACITY);
        let (tx_consensus_to_mempool, rx_consensus_to_mempool) = channel(CHANNEL_CAPACITY);
        let (tx_mempool_to_consensus, rx_mempool_to_consensus) = channel(CHANNEL_CAPACITY);

        // Read the committee and secret key from file.
        let committee = Committee::read(committee_file)?;
        let secret = Secret::read(key_file)?;
        let name = secret.name;
        let secret_key = secret.secret;
        
        

        // Load default parameters if none are specified.
        let parameters = match parameters {
            Some(filename) => Parameters::read(&filename)?,
            None => Parameters::default(),
        };

        let mut firewall: HashMap<u64,Vec<SocketAddr>> = HashMap::new();
        
        //TODO: change below to remove for
        for (key, value) in parameters.network.firewall.clone().into_iter() {
            for address in value { 
                firewall.entry(key).or_insert_with(Vec::new).push(address.parse::<SocketAddr>().unwrap());
            }
        }
        info!("Value for firewall here is {:?}", firewall);
        // Make the data store.
        let store = Store::new(store_path, Block::default().digest()).expect("Failed to create store");

        // Run the signature service.
        let signature_service = SignatureService::new(secret_key);

        // Make a new mempool.
        Mempool::spawn(
            name,
            committee.mempool,
            parameters.mempool,
            store.clone(),
            rx_consensus_to_mempool,
            tx_mempool_to_consensus,
            firewall.clone(),
            parameters.network.allow_communications_at_round,
            parameters.network.network_delay,
        );

        // Run the consensus core.
        Consensus::spawn(
            name,
            committee.consensus,
            parameters.consensus,
            signature_service,
            store,
            rx_mempool_to_consensus,
            tx_consensus_to_mempool,
            tx_commit,
            firewall,
            parameters.network.allow_communications_at_round,
            parameters.network.network_delay,
        );

        info!("Node {} successfully booted", name);
        Ok(Self { commit: rx_commit })
    }

    pub fn print_key_file(filename: &str) -> Result<(), ConfigError> {
        Secret::new().write(filename)
    }

    pub async fn analyze_block(&mut self) {
        while let Some(_block) = self.commit.recv().await {
            // This is where we can further process committed block.
        }
    }
}
