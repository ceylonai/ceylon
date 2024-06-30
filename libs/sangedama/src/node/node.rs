use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::{Duration, SystemTime};

use libp2p::{futures::StreamExt, gossipsub, mdns, swarm::{NetworkBehaviour, Swarm, SwarmEvent}, SwarmBuilder, tcp, noise, yamux};
use libp2p_gossipsub::{MessageId, PublishError};
use log::{debug, error};
use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::sync::mpsc;
use tokio::{io, select};

pub enum EventType {
    OnMessage,
    OnSubscribe,
    OnUnsubscribe,
    OnListen,
    OnExpired,
    OnDiscovered,
    OnConnectionClosed,
    OnConnectionEstablished,
}

impl EventType {
    fn as_str(&self) -> &'static str {
        match self {
            EventType::OnMessage => "OnMessage",
            EventType::OnSubscribe => "OnSubscribe",
            EventType::OnUnsubscribe => "OnUnsubscribe",
            EventType::OnListen => "OnListen",
            EventType::OnExpired => "OnExpired",
            EventType::OnDiscovered => "OnDiscovered",
            EventType::OnConnectionClosed => "OnConnectionClosed",
            EventType::OnConnectionEstablished => "OnConnectionEstablished",
        }
    }
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Eq)]
pub enum MessageType {
    Message,
    Event,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct Message {
    pub data: Vec<u8>,
    pub message: String,
    pub time: u64,
    pub originator: String,
    pub originator_id: String,
    pub r#type: MessageType,
}

impl Message {
    fn new(
        originator: String,
        originator_id: String,
        message: String,
        data: Vec<u8>,
        message_type: MessageType,
    ) -> Self {
        Self {
            data,
            time: SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_millis() as u64,
            originator,
            originator_id,
            r#type: message_type,
            message,
        }
    }
    fn event(originator: String, event: EventType) -> Self {
        Self::new(
            originator,
            "SELF".to_string(),
            event.as_str().to_string(),
            vec![],
            MessageType::Event,
        )
    }

    pub fn data(from: String, originator_id: String, data: Vec<u8>) -> Self {
        Self::new(
            from,
            originator_id,
            "DATA-MESSAGE".to_string(),
            data,
            MessageType::Message,
        )
    }

    fn to_json(&self) -> String {
        json!(self).to_string()
    }
}

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "Event")]
struct NodeBehaviour {
    gossipsub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
}

impl NodeBehaviour {
    fn new(key: &libp2p::identity::Keypair) -> Self {
        let message_id_fn = |message: &gossipsub::Message| {
            let mut s = DefaultHasher::new();
            message.data.hash(&mut s);
            gossipsub::MessageId::from(s.finish().to_string())
        };

        // Set a custom gossipsub configuration
        let gossipsub_config = gossipsub::ConfigBuilder::default()
            .heartbeat_initial_delay(Duration::from_secs(1))
            .history_length(10)
            .history_gossip(10)
            .heartbeat_interval(Duration::from_secs(10)) // This is set to aid debugging by not cluttering the log space
            .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
            .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
            .build()
            .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
            .unwrap(); // Temporary hack because `build` does not return a proper `std::error::Error`.

        // build a gossipsub network behaviour
        let gossipsub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(key.clone()),
            gossipsub_config,
        ).unwrap();

        Self {
            gossipsub,
            mdns: mdns::tokio::Behaviour::new(mdns::Config::default(), key.public().to_peer_id())
                .unwrap(),
        }
    }
}

enum Event {
    Gossipsub(gossipsub::Event),
    Mdns(mdns::Event),
}

impl From<gossipsub::Event> for Event {
    fn from(event: gossipsub::Event) -> Self {
        Event::Gossipsub(event)
    }
}

impl From<mdns::Event> for Event {
    fn from(event: mdns::Event) -> Self {
        Event::Mdns(event)
    }
}

pub struct Node {
    name: String,
    swarm: Swarm<NodeBehaviour>,
    is_leader: bool,
    subscribed_topics: Vec<String>,

    in_rx: mpsc::Receiver<Message>,
    out_tx: mpsc::Sender<Message>,
    pub id: String,
}

impl Node {
    pub fn connect(&mut self, url: &str, topic_str: &str) {
        println!("Connecting to {} with topic {}", url, topic_str);
        // Create a Gossipsub topic
        let topic = gossipsub::IdentTopic::new(topic_str);
        // subscribes to our topic
        self.swarm
            .behaviour_mut()
            .gossipsub
            .subscribe(&topic)
            .unwrap();

        self.swarm.listen_on("/ip4/0.0.0.0/udp/0/quic-v1".parse().unwrap()).unwrap();
        // self.swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse().unwrap()).unwrap();


        // if self.is_leader {
        //     self.swarm
        //         .listen_on(url.to_string().parse().unwrap())
        //         .unwrap();
        // } else {
        //     self.swarm
        //         .dial(url.to_string().parse::<Multiaddr>().unwrap())
        //         .unwrap();
        // }
    }

    pub fn broadcast(&mut self, message: Message) -> Result<Vec<MessageId>, PublishError> {
        let mut message_ids = vec![];
        for topic in self.subscribed_topics.clone() {
            let topic = gossipsub::IdentTopic::new(topic);

            match self
                .swarm
                .behaviour_mut()
                .gossipsub
                .publish(topic, message.to_json().as_bytes())
            {
                Ok(id) => {
                    message_ids.push(id);
                }
                Err(e) => {
                    return Err(e);
                }
            }
        }
        Ok(message_ids)
    }

    async fn pass_message_to_node(&mut self, message: Message) {
        match self.out_tx.clone().send(message).await {
            Ok(_) => {}
            Err(e) => {
                error!("{:?} Failed to send message: {:?}", self.name, e);
            }
        };
    }

    pub async fn run(mut self) {
        loop {
            select! {
                message =  self.in_rx.recv() => match message {
                    Some(message) => {
                        debug!("{:?} Received To Broadcast", self.name);
                        match self.broadcast(message){
                            Ok(message_ids) => {
                                debug!("{:?} Broad casted message: {:?}", self.name, message_ids);

                            }
                            Err(e) => {
                                error!("{:?} Failed to broadcast message: {:?}", self.name, e);
                            }
                        };
                    }
               None => {
                        debug!("{:?} Received: None", self.name);
                    }
                }  ,

                event = self.swarm.select_next_some() => match event {
                         SwarmEvent::NewListenAddr { address, .. } => {
                            debug!("{:?} Listening on {:?}", self.name, address);
                            self.pass_message_to_node(Message::event(self.swarm.local_peer_id().to_string(),EventType::OnListen,)).await

                   },
                        SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            debug!("{:?} Connected to {:?}", self.name, peer_id);
                            self.pass_message_to_node(Message::event(self.swarm.local_peer_id().to_string(),EventType::OnConnectionEstablished,)).await
                        },
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            debug!("{:?} Disconnected from {:?}", self.name, peer_id);
                            self.pass_message_to_node(Message::event(self.swarm.local_peer_id().to_string(),EventType::OnConnectionClosed ,)).await
                        },

                        SwarmEvent::Behaviour(Event::Gossipsub(event)) => {
                            debug!("GOSSIP {:?} {:?}", self.name, event);

                            match event {
                                gossipsub::Event::Message { propagation_source, message_id, message } => {
                                        debug!("{:?} Received message '{:?}' from {:?} on {:?}", self.name, String::from_utf8_lossy(&message.data), propagation_source, message_id);
                                        let msg =  serde_json::from_slice(message.data.as_slice()).unwrap();
                                        self.pass_message_to_node(msg).await
                                },

                                gossipsub::Event::Subscribed { peer_id, topic } => {
                                    debug!("{:?} Subscribed to topic {:?}", self.name, topic.clone().into_string());
                                    self.subscribed_topics.push(topic.into_string());
                                    self.pass_message_to_node(Message::event(  peer_id.to_string(),EventType::OnSubscribe,)).await
                                },

                                _ => {
                                 debug!( "{:?}gossip WILD CARD {:?}", self.name, event);
                            }
                            }
                        },

                        SwarmEvent::Behaviour(Event::Mdns(event)) => {
                            debug!("MDNS {:?} {:?}", self.name, event);

                            match event {
                                mdns::Event::Discovered(list) => {
                                    for (peer_id, _) in list {
                                        self.swarm.behaviour_mut().gossipsub.add_explicit_peer(&peer_id);
                                    }
                                self.pass_message_to_node(Message::event(  self.swarm.local_peer_id().to_string(),EventType::OnDiscovered,)).await
                                },

                                mdns::Event::Expired(list) => {
                                    for (peer_id, _) in list {
                                        self.swarm.behaviour_mut().gossipsub.remove_explicit_peer(&peer_id);
                                    }
                                self.pass_message_to_node(Message::event(  self.swarm.local_peer_id().to_string(),EventType::OnExpired,)).await
                                },
                            }
                        },
                        _ => {
                           debug!( "WILD CARD");
                    }, // Wildcard pattern to cover all other cases
                }
            }
        }
    }
}

pub fn create_node(
    name: String,
    is_leader: bool,
    in_rx: mpsc::Receiver<Message>,
) -> (Node, mpsc::Receiver<Message>) {
    let swarm = SwarmBuilder::with_new_identity()
        .with_tokio()
        .with_tcp(
            tcp::Config::default(),
            noise::Config::new,
            yamux::Config::default,
        ).unwrap()
        .with_quic()
        .with_behaviour(|key| {
            Ok(NodeBehaviour::new(key))
        })
        .unwrap()
        .build();

    let (out_tx, _rx) = mpsc::channel(100);

    (
        Node {
            name,
            id: swarm.local_peer_id().to_string(),
            swarm,
            is_leader,
            subscribed_topics: Vec::new(),
            in_rx,
            out_tx,
        },
        _rx,
    )
}

// Create test
#[cfg(test)]
mod tests {
    use log::{debug, info, trace, warn};
    use serde_json::json;

    use crate::node::node::{create_node, Message};

    #[test]
    fn test_ping() {
        env_logger::init();
        let port_id = 8888;
        let topic = "test_topic";

        let url = format!("/ip4/0.0.0.0/tcp/{}", port_id);

        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (tx_1, mut rx_1) = tokio::sync::mpsc::channel::<Message>(100);

        let (mut node_0, mut rx_o_0) = create_node("node_0".to_string(), true, rx_0);
        let (mut node_1, mut rx_o_1) = create_node("node_1".to_string(), false, rx_1);

        let node_0_id = node_0.id.clone();
        let node_1_id = node_1.id.clone();

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();

        runtime.spawn(async move {
            while let Some(message_data) = rx_o_0.recv().await {
                debug!("Node_0 Received: {:?}", message_data);
                let msg = Message::data(
                    "node_0".to_string(),
                    node_0_id.clone(),
                    json!({
                        "data": format!("Hi from Node_0: {}", message_data.message).as_str(),
                    })
                        .to_string()
                        .as_bytes()
                        .to_vec(),
                );
                tx_0.send(msg).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(3000)).await;
            }
        });

        runtime.spawn(async move {
            while let Some(message_data) = rx_o_1.recv().await {
                debug!("Node_1 Received: {:?}", message_data);
                let msg = Message::data(
                    "node_1".to_string(),
                    node_1_id.clone(),
                    json!({
                        "data": format!("Hi from Node_1: {}", message_data.message).as_str(),
                    })
                        .to_string()
                        .as_bytes()
                        .to_vec(),
                );
                tx_1.send(msg).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(3000)).await;
            }
        });
        let url_ = url.clone();
        runtime.spawn(async move {
            node_0.connect(url_.clone().as_str(), topic);
            node_0.run().await;
        });
        let url_ = url.clone();
        runtime.block_on(async move {
            // wait for 1 event to make sure swarm0 is listening
            tokio::time::sleep(std::time::Duration::from_millis(10000)).await;

            node_1.connect(url_.clone().as_str(), topic);
            node_1.run().await;
        });
    }
}
