use crate::config::{Committee, Parameters};//, NetworkParameters};
use crate::core::Core;
use crate::error::ConsensusError;
use crate::helper::Helper;
use crate::leader::LeaderElector;
use crate::mempool::MempoolDriver;
use crate::messages::{Block, Timeout, Vote, TC, Blocks};
use crate::proposer::Proposer;
use crate::synchronizer::Synchronizer;
use async_trait::async_trait;
use bytes::Bytes;
use crypto::{Digest, PublicKey, SignatureService};
use futures::SinkExt as _;
use log::info;
use mempool::ConsensusMempoolMessage;
use network::{MessageHandler, Receiver as NetworkReceiver, Writer};
use serde::{Deserialize, Serialize};
use std::error::Error;
use store::Store;
use tokio::sync::mpsc::{channel, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::net::SocketAddr;
use lazy_static::lazy_static;
use std::collections::HashMap;

#[cfg(test)]
#[path = "tests/consensus_tests.rs"]
pub mod consensus_tests;

/// The default channel capacity for each channel of the consensus.
pub const CHANNEL_CAPACITY: usize = 1_000;


lazy_static! {
    pub static ref REQUEST_BLOCKS: Arc<Mutex<u64>> = Arc::new(Mutex::new(10_u64));
    pub static ref REQUEST_CLIQUES: Arc<Mutex<HashMap<PublicKey, Vec<SocketAddr>>>> = Arc::new(Mutex::new(HashMap::new()));
}


/// pub static mut REQUEST_BLOCKS: u64 = 10;
/// The consensus round number.
pub type Round = u64;

#[derive(Serialize, Deserialize, Debug)]
pub enum ConsensusMessage {
    Propose(Block),
    Vote(Vote),
    Timeout(Timeout),
    TC(TC),
    SyncRequest(Digest, PublicKey),
    NewSyncRequest(Digest, u64, PublicKey),
    Blocks(Blocks),
    FirstBlocks(Blocks, Vec<SocketAddr>),
    ShiftedChain(PublicKey, Vec<SocketAddr>),
}

pub struct Consensus;

impl Consensus {
    #[allow(clippy::too_many_arguments)]
    pub fn spawn(
        name: PublicKey,
        committee: Committee,
        parameters: Parameters,
        signature_service: SignatureService,
        store: Store,
        rx_mempool: Receiver<Digest>,
        tx_mempool: Sender<ConsensusMempoolMessage>,
        tx_commit: Sender<Block>,
        firewall: HashMap<u64, Vec<SocketAddr>>,
        allow_communications_at_round: u64,
        network_delay: u64,
    ) {
        // NOTE: This log entry is used to compute performance.
        parameters.log();

        let (tx_consensus, rx_consensus) = channel(CHANNEL_CAPACITY);
        let (tx_loopback, rx_loopback) = channel(CHANNEL_CAPACITY);
        let (tx_proposer, rx_proposer) = channel(CHANNEL_CAPACITY);
        let (tx_helper, rx_helper) = channel(CHANNEL_CAPACITY);

        // Spawn the network receiver.
        let mut address = committee
            .address(&name)
            .expect("Our public key is not in the committee");
        address.set_ip("0.0.0.0".parse().unwrap());
        NetworkReceiver::spawn(
            address,
            /* handler */
            ConsensusReceiverHandler {
                tx_consensus,
                tx_helper,
                //tx_new_helper,
            },
        );
        info!(
            "Node {} listening to consensus messages on {}",
            name, address
        );

        // Make the leader election module.
        let leader_elector = LeaderElector::new(committee.clone());

        // Make the mempool driver.
        let mempool_driver = MempoolDriver::new(store.clone(), tx_mempool, tx_loopback.clone());

        // Make the synchronizer.
        let synchronizer = Synchronizer::new(
            name,
            committee.clone(),
            store.clone(),
            tx_loopback.clone(),
            parameters.sync_retry_delay,
            firewall.clone(),
            allow_communications_at_round,
            network_delay,
        );

        // Spawn the consensus core.
        Core::spawn(
            name,
            committee.clone(),
            signature_service.clone(),
            store.clone(),
            leader_elector,
            mempool_driver,
            synchronizer,
            parameters.timeout_delay,
            /* rx_message */ rx_consensus,
            rx_loopback,
            tx_proposer,
            tx_commit,
            firewall.clone(),
            allow_communications_at_round,
            network_delay,
        );

        // Spawn the block proposer.
        Proposer::spawn(
            name,
            committee.clone(),
            signature_service,
            rx_mempool,
            /* rx_message */ rx_proposer,
            tx_loopback,
            firewall.clone(),
            allow_communications_at_round,
            network_delay,
        );

        // Spawn the helper module.
        Helper::spawn(committee.clone(), store.clone(), /* rx_requests */ rx_helper, network_delay);
    }
}

/// Defines how the network receiver handles incoming primary messages.
#[derive(Clone)]
struct ConsensusReceiverHandler {
    tx_consensus: Sender<ConsensusMessage>,
    tx_helper: Sender<(Digest, PublicKey)>,
}

#[async_trait]
impl MessageHandler for ConsensusReceiverHandler {
    async fn dispatch(&self, writer: &mut Writer, serialized: Bytes) -> Result<(), Box<dyn Error>> {
        // Deserialize and parse the message.
        match bincode::deserialize(&serialized).map_err(ConsensusError::SerializationError)? {
            ConsensusMessage::SyncRequest(missing, origin) => {info!("Received sync request {:?}", missing.clone()); self
                .tx_helper
                .send((missing, origin))
                .await
                .expect("Failed to send consensus message")},
            message @ ConsensusMessage::NewSyncRequest(..) => {
                let _ = writer.send(Bytes::from("Ack")).await;
                info!("Received new sync request. Responded with an ack ");
                self.tx_consensus
                    .send(message)
                    .await
                    .expect("Failed to send consensus message")
                
            },
            message @ ConsensusMessage::FirstBlocks(..) => {
                let _ = writer.send(Bytes::from("Ack")).await;

                self.tx_consensus
                    .send(message)
                    .await
                    .expect("Failed to send consensus message")
            },
            message @ ConsensusMessage::Blocks(..) => {
                let _ = writer.send(Bytes::from("Ack")).await;

                self.tx_consensus
                    .send(message)
                    .await
                    .expect("Failed to send consensus message")
            },
            message @ ConsensusMessage::ShiftedChain(..) => {
                info!("Sending ack for shifted received");
                // Reply with an ACK.
                let _ = writer.send(Bytes::from("Ack")).await;

                // Pass the message to the consensus core.
                self.tx_consensus
                    .send(message)
                    .await
                    .expect("Failed to consensus message")
            },
            message @ ConsensusMessage::Propose(..) => {
                // Reply with an ACK.
                let _ = writer.send(Bytes::from("Ack")).await;

                // Pass the message to the consensus core.
                self.tx_consensus
                    .send(message)
                    .await
                    .expect("Failed to consensus message")
            },           
            message => self
                .tx_consensus
                .send(message)
                .await
                .expect("Failed to consensus message"),
        }
        Ok(())
    }
}
