use std::time::{SystemTime, UNIX_EPOCH};

use hex;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

type BlockData = Vec<u8>;
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Block {
    index: u64,
    timestamp: u128,
    previous_hash: String,
    hash: String,
    data: BlockData,
    nonce: u64,
}

impl Block {
    fn new(index: u64, previous_hash: String, data: BlockData) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_millis();
        let mut block = Block {
            index,
            timestamp,
            previous_hash,
            hash: String::new(),
            data,
            nonce: 0,
        };
        block.hash = block.calculate_hash();
        block
    }

    fn calculate_hash(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.index.to_string());
        hasher.update(self.timestamp.to_string());
        hasher.update(&self.previous_hash);
        hasher.update(&self.data);
        hasher.update(self.nonce.to_string());
        let result = hasher.finalize();
        hex::encode(result)
    }

    fn mine_block(&mut self, difficulty: usize) {
        let target = "0".repeat(difficulty);
        while &self.hash[..difficulty] != target {
            self.nonce += 1;
            self.hash = self.calculate_hash();
        }
    }
}

pub struct Blockchain {
    blocks: Vec<Block>,
    difficulty: usize,
}

impl Blockchain {
    pub(crate) fn new(difficulty: usize) -> Self {
        let mut blockchain = Blockchain {
            blocks: vec![Block::new(0, String::from("0"), String::from("Genesis Block").into_bytes())],
            difficulty,
        };
        blockchain.blocks[0].hash = blockchain.blocks[0].calculate_hash();
        blockchain
    }

    pub(crate) fn add_block(&mut self, data: BlockData) {
        let previous_block = &self.blocks[self.blocks.len() - 1];
        let mut new_block = Block::new(self.blocks.len() as u64, previous_block.hash.clone(), data);
        new_block.mine_block(self.difficulty);
        self.blocks.push(new_block);
    }

    pub(crate) fn is_valid(&self) -> bool {
        for i in 1..self.blocks.len() {
            let current_block = &self.blocks[i];
            let previous_block = &self.blocks[i - 1];

            if current_block.hash != current_block.calculate_hash() {
                return false;
            }
            if current_block.previous_hash != previous_block.hash {
                return false;
            }
        }
        true
    }

    pub fn get_last(&self) -> &Block {
        self.blocks.last().unwrap()
    }
}

