use crate::types::TransportStatus;
use async_trait::async_trait;
use std::error::Error;
use tokio::sync::mpsc::Sender;
pub mod p2p;

#[async_trait]
pub trait Transporter {
    fn new(tx: Sender<TransportStatus>, owner: String) -> Self;
    fn get_tx(&mut self) -> Sender<String>;
    async fn message_processor(&mut self) -> Result<(), Box<dyn Error>>;
}
