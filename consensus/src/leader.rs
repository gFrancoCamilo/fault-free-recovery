use crate::config::{Committee};
use crate::consensus::Round;
use crypto::PublicKey;
use std::net::{SocketAddr};

pub type LeaderElector = RRLeaderElector;

pub struct RRLeaderElector {
    committee: Committee,
}

impl RRLeaderElector {
    pub fn new(committee: Committee) -> Self {
        Self { committee }
    }
    pub fn get_leader(&self, round: Round, _firewall: Vec<SocketAddr>) -> PublicKey {
        let mut keys: Vec<_> = self.committee.authorities.keys().cloned().collect();
        keys.sort();
        keys[round as usize % self.committee.size()]
    }
}
