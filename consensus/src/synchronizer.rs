use crate::config::Committee;
use crate::consensus::{ConsensusMessage, CHANNEL_CAPACITY, REQUEST_BLOCKS};
use crate::error::ConsensusResult;
use crate::messages::{Block, QC};
use bytes::Bytes;
use crypto::Hash as _;
use crypto::{Digest, PublicKey};
use futures::stream::futures_unordered::FuturesUnordered;
use futures::stream::StreamExt as _;
use log::{debug, error};
use network::SimpleSender;
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};
use store::Store;
use tokio::sync::mpsc::{channel, Receiver, Sender};
use tokio::time::{sleep, Duration, Instant};
use std::net::SocketAddr;

#[cfg(test)]
#[path = "tests/synchronizer_tests.rs"]
pub mod synchronizer_tests;

const TIMER_ACCURACY: u64 = 5_000;

pub struct Synchronizer {
    store: Store,
    inner_channel: Sender<Block>,
    blocks_channel: Sender<(Block, PublicKey)>,
}

impl Synchronizer {
    pub fn new(
        name: PublicKey,
        committee: Committee,
        store: Store,
        tx_loopback: Sender<Block>,
        sync_retry_delay: u64,
        _firewall: HashMap<u64,Vec<SocketAddr>>,
        _allow_communications_at_round: u64,
        network_delay: u64,
    ) -> Self {
        let mut network = SimpleSender::new(network_delay);
        let (tx_inner, mut rx_inner): (_, Receiver<Block>) = channel(CHANNEL_CAPACITY);
        let (tx_blocks, mut rx_blocks): (_, Receiver<(Block, PublicKey)>) = channel(CHANNEL_CAPACITY);

        let store_copy = store.clone();
        tokio::spawn(async move {
            let mut waiting = FuturesUnordered::new();
            let mut pending = HashSet::new();
            let mut requests = HashMap::new();

            let timer = sleep(Duration::from_millis(TIMER_ACCURACY));
            tokio::pin!(timer);
            loop {
                tokio::select! {
                    Some(block) = rx_inner.recv() => {
                        if pending.insert(block.digest()) {
                            let parent = block.parent().clone();
                            let author = block.author;
                            let fut = Self::waiter(store_copy.clone(), parent.clone(), block);
                            waiting.push(fut);

                            if !requests.contains_key(&parent){
                                debug!("Requesting sync for block {}", parent);
                                let now = SystemTime::now()
                                    .duration_since(UNIX_EPOCH)
                                    .expect("Failed to measure time")
                                    .as_millis();
                                requests.insert(parent.clone(), now);
                                let address = committee
                                    .address(&author)
                                    .expect("Author of valid block is not in the committee");
                                let message = ConsensusMessage::SyncRequest(parent, name);
                                let message = bincode::serialize(&message)
                                    .expect("Failed to serialize sync request");
                                network.send(address, Bytes::from(message)).await;
                            }
                        }
                    },
                    Some((block, sender)) = rx_blocks.recv() => {
                        if pending.insert(block.digest()) {
                            let parent = block.parent().clone();
                            let author = sender;
                            let fut = Self::waiter(store_copy.clone(), parent.clone(), block);
                            waiting.push(fut);

                            if !requests.contains_key(&parent){
                                debug!("Requesting new sync for block {}", parent);
                                let now = SystemTime::now()
                                    .duration_since(UNIX_EPOCH)
                                    .expect("Failed to measure time")
                                    .as_millis();
                                requests.insert(parent.clone(), now);
                                let address = committee
                                    .address(&author)
                                    .expect("Author of valid block is not in the committee");

                                let blocks: u64;
                                { 
                                    let my_lock = REQUEST_BLOCKS.lock().unwrap();
                                    blocks = *my_lock;
                                }
                                let message = ConsensusMessage::NewSyncRequest(parent, blocks, name);
                                let message = bincode::serialize(&message)
                                    .expect("Failed to serialize sync request");
                                debug!("Sending new sync request to this address {:?}", address);
                                network.send(address, Bytes::from(message)).await;
                                //handler.await;

                            }
                        }
                    },
                    Some(result) = waiting.next() => match result {
                        Ok(block) => {
                            let _ = pending.remove(&block.digest());
                            let _ = requests.remove(block.parent());
                            if let Err(e) = tx_loopback.send(block).await {
                                panic!("Failed to send message through core channel: {}", e);
                            }
                        },
                        Err(e) => error!("{}", e)
                    },
                    () = &mut timer => {
                        // This implements the 'perfect point to point link' abstraction.
                        for (digest, timestamp) in &requests {
                            let now = SystemTime::now()
                                .duration_since(UNIX_EPOCH)
                                .expect("Failed to measure time")
                                .as_millis();
                            if timestamp + (sync_retry_delay as u128) < now {
                                debug!("Requesting sync for block {} (retry)", digest);
                                let addresses = committee
                                    .broadcast_addresses(&name)
                                    .into_iter()
                                    .map(|(_, x)| x)
                                    .collect();
                                let message = ConsensusMessage::SyncRequest(digest.clone(), name);
                                let message = bincode::serialize(&message)
                                    .expect("Failed to serialize sync request");
                                network.broadcast(addresses, Bytes::from(message)).await;
                            }
                        }
                        timer.as_mut().reset(Instant::now() + Duration::from_millis(TIMER_ACCURACY));
                    }
                }
            }
        });
        Self {
            store,
            inner_channel: tx_inner,
            blocks_channel: tx_blocks,
        }
    }

    async fn waiter(mut store: Store, wait_on: Digest, deliver: Block) -> ConsensusResult<Block> {
        let _ = store.notify_read(wait_on.to_vec()).await?;
        Ok(deliver)
    }

    pub async fn sync_blocks(&mut self, block: &Block, sender: PublicKey) -> ConsensusResult<Option<Block>> {
        if let Err(e) = self.blocks_channel.send((block.clone(), sender.clone())).await {
            panic!("Failed to send request to synchronizer: {}", e);
        }
        Ok(None)
    }
    pub async fn get_parent_block(&mut self, block: &Block) -> ConsensusResult<Option<Block>> {
        if block.qc == QC::genesis() {
            return Ok(Some(Block::genesis()));
        }
        let parent = block.parent();
        match self.store.read(parent.to_vec()).await? {
            Some(bytes) => Ok(Some(bincode::deserialize(&bytes)?)),
            None => {
                if let Err(e) = self.inner_channel.send(block.clone()).await {
                    panic!("Failed to send request to synchronizer: {}", e);
                }
                Ok(None)
            }
        }
    }

    /*pub async fn get_b_ancestors(&mut self, block: &Block, num_blocks: u64) -> ConsensusResult<Option<Vec<Block>>> {
        let mut ancestors = Vec::new();
        ancestors.push(block.clone());
        let mut i = 1;
        let mut tip = block.clone();
        while i < num_blocks{
            /*ancestors.push(match self.get_parent_block(block).await? {
                Some(b) => &b,
                None => todo!(),
            });*/
            match self.get_parent_block(&tip).await? {
                Some(b) => {tip = b.clone(); 
                    ancestors.push(b);},
                None => todo!(),
            };
            i = i + 1;
        }
        Ok(Some(ancestors))
    }*/

    pub async fn get_ancestors(
        &mut self,
        block: &Block,
    ) -> ConsensusResult<Option<(Block, Block)>> {
        let b1 = match self.get_parent_block(block).await? {
            Some(b) => b,
            None => return Ok(None),
        };
        let b0 = self
            .get_parent_block(&b1)
            .await?
            .expect("We should have all ancestors of delivered blocks");
        Ok(Some((b0, b1)))
    }
}
