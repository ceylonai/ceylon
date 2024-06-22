use std::collections::HashSet;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Block {
    pub index: u64,
    pub timestamp: u64,
    pub message: Vec<u8>,
    pub previous_hash: String,
    pub hash: String,
}

pub struct Blockchain {
    pub chain: Vec<Block>,
}

impl Blockchain {
    pub fn new() -> Self {
        Self {
            chain: vec![],
        }
    }

    pub fn init_block(&mut self) {
        let genesis_block = Block {
            index: 0,
            timestamp: Self::current_timestamp(),
            message: vec![],
            previous_hash: String::new(),
            hash: String::new(),
        };
        self.chain.push(genesis_block);
    }

    pub fn add_block(&mut self, message: Vec<u8>) {
        let previous_block = self.chain.last().unwrap().clone();
        let index = previous_block.index + 1;
        let previous_hash = previous_block.hash.clone();
        let hash = Self::hash_block(&previous_block);
        let timestamp = Self::current_timestamp();
        let new_block = Block { index, timestamp, message, previous_hash, hash };
        self.chain.push(new_block);
        self.remove_duplicates();
        self.reorder_blocks_by_time();
    }

    fn reorder_blocks_by_time(&mut self) {
        self.chain.sort_by_key(|block| block.timestamp);
        self.reindex_chain();
    }

    fn reindex_chain(&mut self) {
        for (i, block) in self.chain.iter_mut().enumerate() {
            block.index = i as u64;
        }
    }

    pub fn remove_duplicates(&mut self) {
        let mut unique_blocks = HashSet::new();
        self.chain.retain(|block| {
            let key = (block.index, block.timestamp);
            unique_blocks.insert(key)
        });
        self.reindex_chain();
    }

    fn current_timestamp() -> u64 {
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
    }

    fn hash_block(block: &Block) -> String {
        // Here you should implement a proper hash function for your block
        format!("{}_{}", block.index, block.timestamp)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_blockchain_initialization() {
        let blockchain = Blockchain::new();
        assert!(blockchain.chain.is_empty());
    }

    #[test]
    fn test_init_block() {
        let mut blockchain = Blockchain::new();
        blockchain.init_block();
        assert_eq!(blockchain.chain.len(), 1);
        let genesis_block = &blockchain.chain[0];
        assert_eq!(genesis_block.clone().index, 0);
        assert_eq!(genesis_block.clone().message.len(), 0);
        assert_eq!(genesis_block.clone().previous_hash, String::new());
    }

    #[test]
    fn test_add_block() {
        let mut blockchain = Blockchain::new();
        blockchain.init_block();
        blockchain.add_block(b"First block".to_vec());
        assert_eq!(blockchain.chain.len(), 2);
        let first_block = &blockchain.chain[1];
        assert_eq!(first_block.index, 1);
        assert_eq!(first_block.message, b"First block".to_vec());
    }

    #[test]
    fn test_reorder_blocks_by_time() {
        let mut blockchain = Blockchain::new();
        blockchain.init_block();

        let mut block1 = Block {
            index: 1,
            timestamp: 100,
            message: b"Block 1".to_vec(),
            previous_hash: String::new(),
            hash: String::new(),
        };
        let mut block2 = Block {
            index: 2,
            timestamp: 50,
            message: b"Block 2".to_vec(),
            previous_hash: String::new(),
            hash: String::new(),
        };

        blockchain.chain.push(block1.clone());
        blockchain.chain.push(block2.clone());

        blockchain.reorder_blocks_by_time();

        assert_eq!(blockchain.chain[0].timestamp, 50);
        assert_eq!(blockchain.chain[1].timestamp, 100);
    }

    #[test]
    fn test_remove_duplicates() {
        let mut blockchain = Blockchain::new();
        blockchain.init_block();

        let block = Block {
            index: 1,
            timestamp: 100,
            message: b"Block".to_vec(),
            previous_hash: String::new(),
            hash: String::new(),
        };

        blockchain.chain.push(block.clone());
        blockchain.chain.push(block.clone());
        blockchain.chain.push(block.clone());
        blockchain.chain.push(block.clone());

        assert_eq!(blockchain.chain.len(), 5);
        blockchain.remove_duplicates();

        assert_eq!(blockchain.chain.len(), 2);
        assert_eq!(blockchain.chain[1].timestamp, 100);
    }

    #[test]
    fn test_reindex_chain() {
        let mut blockchain = Blockchain::new();
        blockchain.init_block();

        let block = Block {
            index: 1,
            timestamp: 100,
            message: b"Block".to_vec(),
            previous_hash: String::new(),
            hash: String::new(),
        };

        blockchain.chain.push(block.clone());
        blockchain.reindex_chain();

        assert_eq!(blockchain.chain[1].index, 1);
    }

    #[test]
    fn test_hash_block() {
        let block = Block {
            index: 1,
            timestamp: 100,
            message: b"Block".to_vec(),
            previous_hash: String::new(),
            hash: String::new(),
        };

        let hash = Blockchain::hash_block(&block);
        assert_eq!(hash, "1_100");
    }
}

