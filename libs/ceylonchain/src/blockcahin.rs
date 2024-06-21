use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};
use chrono::prelude::*;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Block {
    pub index: u32,
    pub timestamp: i64,
    pub previous_hash: String,
    pub hash: String,
    pub data: Vec<u8>,
}

impl Block {
    pub fn new(index: u32, previous_hash: String, data: Vec<u8>) -> Self {
        let timestamp = Utc::now().timestamp();
        let hash = Block::calculate_hash(index, timestamp, &previous_hash, &data);
        Block {
            index,
            timestamp,
            previous_hash,
            hash,
            data,
        }
    }

    pub fn calculate_hash(index: u32, timestamp: i64, previous_hash: &str, data: &[u8]) -> String {
        let input = format!("{}{}{}{:?}", index, timestamp, previous_hash, data);
        let mut hasher = Sha256::new();
        hasher.update(input);
        let result = hasher.finalize();
        let hex_result = hex::encode(result);
        format!("{}", hex_result)
    }
}

#[derive(Debug)]
pub struct Blockchain {
    pub blocks: Vec<Block>,
}

impl Blockchain {
    pub fn new() -> Self {
        let mut blockchain = Blockchain { blocks: Vec::new() };
        blockchain.add_block("Genesis Block".to_string().into_bytes());
        blockchain
    }

    pub fn add_block(&mut self, data: Vec<u8>) {
        let index = self.blocks.len() as u32;
        let previous_hash = if index == 0 {
            "0".to_string()
        } else {
            self.blocks[index as usize - 1].hash.clone()
        };
        let block = Block::new(index, previous_hash, data);
        self.blocks.push(block);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_creation() {
        let data = "Test Data".to_string();
        let previous_hash = "0".to_string();
        let block = Block::new(0, previous_hash.clone(), data.clone().into_bytes());

        // Verify fields
        assert_eq!(block.index, 0);
        assert!(block.timestamp > 0);  // Ensure a valid timestamp
        assert_eq!(block.previous_hash, previous_hash);
        assert_ne!(block.hash, ""); // Hash shouldn't be empty
        assert_eq!(block.data, data.clone().into_bytes());

        // Verify hash calculation
        let calculated_hash = Block::calculate_hash(0, block.timestamp, &previous_hash, &data.into_bytes());
        assert_eq!(block.hash, calculated_hash);
    }

    #[test]
    fn test_blockchain_creation_and_genesis_block() {
        let blockchain = Blockchain::new();

        // Check initial length
        assert_eq!(blockchain.blocks.len(), 1);

        // Check genesis block
        let genesis_block = &blockchain.blocks[0];
        assert_eq!(genesis_block.index, 0);
        assert_eq!(genesis_block.previous_hash, "0");
        assert_eq!(String::from_utf8(genesis_block.data.clone()).unwrap(), "Genesis Block");
    }

    #[test]
    fn test_adding_blocks_to_blockchain() {
        let mut blockchain = Blockchain::new();

        let data1 = "Block 1 Data".to_string();
        blockchain.add_block(data1.clone().into_bytes());
        assert_eq!(blockchain.blocks.len(), 2);

        let block1 = &blockchain.blocks[1].clone();
        let block_0_hash = blockchain.blocks[0].hash.clone();
        assert_eq!(block1.index, 1);
        assert_eq!(block1.previous_hash, block_0_hash);
        assert_eq!(String::from_utf8(block1.data.clone()).unwrap(), data1);
        let data2 = "Block 2 Data".to_string();
        blockchain.add_block(data2.clone().into_bytes());
        assert_eq!(blockchain.blocks.len(), 3);

        let block2 = &blockchain.blocks[2];
        assert_eq!(block2.index, 2);
        assert_eq!(block2.previous_hash, block1.hash);
        assert_eq!(String::from_utf8(block2.data.clone()).unwrap(), data2);
    }
}