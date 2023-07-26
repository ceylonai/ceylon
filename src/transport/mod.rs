use std::error::Error;
use async_trait::async_trait;
use tokio::sync::mpsc::Sender;
use crate::types::TransportStatus;
pub mod p2p;


#[async_trait]
pub trait Transporter {
    fn new(
        tx: Sender<TransportStatus>,
        owner: String,
    ) -> Self;
    fn get_tx(&mut self) -> Sender<String>;
    async fn message_processor(&mut self) -> Result<(), Box<dyn Error>>;
}