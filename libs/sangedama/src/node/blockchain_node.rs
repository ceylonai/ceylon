use sha2::{Sha256, Digest};
use chrono::Utc;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Block {
    index: u64,
    timestamp: i64,
    data: Vec<u8>,
    previous_hash: String,
    hash: String,
}

#[derive(Debug)]
struct Blockchain {
    chain: Vec<Block>,
}

impl Block {
    fn new(index: u64, data: Vec<u8>, previous_hash: String) -> Self {
        let timestamp = Utc::now().timestamp();
        let mut block = Block {
            index,
            timestamp,
            data,
            previous_hash,
            hash: String::new(),
        };
        block.hash = block.calculate_hash();
        block
    }

    fn calculate_hash(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(format!("{}{}{:?}{}", self.index, self.timestamp, self.data, self.previous_hash));
        format!("{:x}", hasher.finalize())
    }
}

impl Blockchain {
    fn new() -> Self {
        let genesis_block = Block::new(0, String::from("Genesis Block").as_bytes().to_vec(), String::from("0"));
        Blockchain {
            chain: vec![genesis_block],
        }
    }

    fn add_block(&mut self, data: Vec<u8>) {
        let previous_block = self.chain.last().unwrap();
        let new_block = Block::new(
            previous_block.index + 1,
            data,
            previous_block.hash.clone(),
        );
        self.chain.push(new_block);
    }

    fn is_chain_valid(&self) -> bool {
        for i in 1..self.chain.len() {
            let current_block = &self.chain[i];
            let previous_block = &self.chain[i - 1];

            if current_block.hash != current_block.calculate_hash() {
                return false;
            }

            if current_block.previous_hash != previous_block.hash {
                return false;
            }
        }
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;


    #[test]
    fn test_block() {
        let mut blockchain = Blockchain::new();

        blockchain.add_block(String::from("First Block").as_bytes().to_vec());
        blockchain.add_block(String::from("Second Block").as_bytes().to_vec());
        blockchain.add_block(String::from("Third Block").as_bytes().to_vec());

        println!("{:#?}", blockchain);
        println!("Is blockchain valid? {}", blockchain.is_chain_valid());
    }
}