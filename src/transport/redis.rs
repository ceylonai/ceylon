use std::error::Error;
use std::sync::Arc;

use async_trait::async_trait;
use futures::StreamExt;
use log::{debug, error, info};
use redis::{Commands, PubSubCommands};
use tokio::sync::{mpsc, Mutex};
use tokio::sync::mpsc::{Receiver, Sender};

use crate::transport::Transporter;
use crate::types::{TransportMessage, TransportStatus};

pub struct RedisTransporter {
    peer_id: String,
    channel: String,
    owner: String,
    rx: Arc<Mutex<Receiver<String>>>,
    tx: Sender<String>,
    msg_tx: Sender<TransportStatus>,
}

async fn SendStatus(msg_tx: Sender<TransportStatus>, status: TransportStatus) {
    match msg_tx.clone().send(status).await {
        Ok(_) => {
            debug!("Sent message");
        }
        Err(e) => {
            error!("error {}", e);
        }
    };
}

#[async_trait]
impl Transporter for RedisTransporter {
    fn new(msg_tx: Sender<TransportStatus>, owner: String) -> Self {
        let (tx, rx) = mpsc::channel(32);
        let peer_id = nanoid::nanoid!();
        RedisTransporter {
            peer_id,
            channel: String::from("ABC"),
            rx: Arc::new(Mutex::new(rx)),
            tx,
            msg_tx,
            owner,
        }
    }

    fn get_tx(&mut self) -> Sender<String> {
        self.tx.clone()
    }

    async fn message_processor(&mut self) -> Result<(), Box<dyn Error>> {
        let channel_name = self.channel.clone();

        let peer_id = self.peer_id.clone();
        let name = self.owner.clone();

        info!("Agent {} Stared at: {}", name, peer_id);

        let msg_tx = self.msg_tx.clone();
        let t1 = tokio::spawn(async move {
            let client = redis::Client::open("redis://127.0.0.1/").unwrap();
            let mut conn = client.get_async_connection().await.unwrap();
            let mut pubsub = conn.into_pubsub();
            pubsub.subscribe(channel_name).await.unwrap();

            let mut stream = pubsub.on_message();
            while let msg = stream.next() {
                let msg = msg.await.unwrap();
                let payload = msg.get_payload_bytes().to_vec();
                let data = TransportMessage::from_bytes(payload.clone());
                let data_log = TransportMessage::from_bytes(payload);
                if data.sender_id == name { continue; }
                debug!("Received message from Agent: {:?}-{}-{}", data_log.data, data_log.sender_id, name);
                SendStatus(msg_tx.clone(), TransportStatus::Data(data)).await;
            }
            debug!("Listening for messages end");
        });

        let rx = self.rx.clone();

        let peer_id = self.peer_id.clone();
        let msg_tx = self.msg_tx.clone();
        let owner_name = self.owner.clone();
        let channel_name = self.channel.clone();
        let t2 = tokio::spawn(async move {
            let client = redis::Client::open("redis://127.0.0.1/").unwrap();
            let mut conn = client.get_connection().unwrap();
            SendStatus(msg_tx, TransportStatus::Started).await;
            let mut rx = rx.lock().await;
            loop {
                tokio::select! {
                    message = rx.recv() => {
                        let message =  match message{
                            Some(msg) => msg,
                            None => continue
                        };
                        let server_message = TransportMessage::using_bytes(message.clone(),owner_name.to_string(),owner_name.clone());
                        let _: () = conn.publish(&channel_name, &server_message).unwrap();
                        debug!("Publish message from Agent {}: {:?}", owner_name,message);
                    }
                }
            }
        });


        tokio::select! {
            _ = t2 => {
                debug!("Listening for t2");
            }
        _ = t1 => {
            debug!("Listening for t1");
        }
    }
        Ok(())
    }
}