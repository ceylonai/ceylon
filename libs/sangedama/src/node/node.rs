use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::{Duration, SystemTime};

use libp2p::{
    futures::StreamExt,
    gossipsub, mdns,
    swarm::{NetworkBehaviour, Swarm, SwarmEvent},
    Multiaddr, SwarmBuilder,
};
use libp2p_gossipsub::{MessageId, PublishError};
use serde_json::json;
use tokio::sync::mpsc;
use tokio::{io, select, spawn};

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "Event")]
struct NodeBehaviour {
    gossipsub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
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

    in_rx: tokio::sync::mpsc::Receiver<Vec<u8>>,
    out_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
}

impl Node {
    pub fn connect(&mut self, port: u16, topic_str: &str) {
        // Create a Gossipsub topic
        let topic = gossipsub::IdentTopic::new(topic_str);
        // subscribes to our topic
        self.swarm
            .behaviour_mut()
            .gossipsub
            .subscribe(&topic)
            .unwrap();
        if self.is_leader {
            self.swarm
                .listen_on(format!("/ip4/0.0.0.0/tcp/{}", port).parse().unwrap())
                .unwrap();
        } else {
            self.swarm
                .dial(
                    format!("/ip4/0.0.0.0/tcp/{}", port)
                        .parse::<Multiaddr>()
                        .unwrap(),
                )
                .unwrap();
        }
    }

    pub fn broadcast(&mut self, message: &[u8]) -> Result<Vec<MessageId>, PublishError> {
        let mut message_ids = vec![];
        for topic in self.subscribed_topics.clone() {
            let topic = gossipsub::IdentTopic::new(topic);
            match self.swarm.behaviour_mut().gossipsub.publish(topic, message) {
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

    pub async fn run(mut self) {
        // let swarm_behaviour = self.swarm.behaviour_mut();
        // let subscribed_topics = self.subscribed_topics.clone();
        // while let Some(message) = self.in_rx.recv().await {
        //     // println!("Received: {:?}", String::from_utf8_lossy(&message));
        //
        // }

        loop {
            select! {

                message =  self.in_rx.recv() => match message {
                    Some(message) => {
                        println!("{:?} Received: {:?}", self.name, String::from_utf8_lossy(&message));
                        self.broadcast( json!({
                    "data": String::from_utf8_lossy(&message),
                    "timestamp": SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_millis()
                }).to_string().as_bytes()).unwrap();
                    }
                    None => {
                        println!("{:?} Received: None", self.name);
                    }
                }  ,

                event = self.swarm.select_next_some() => match event {
                         SwarmEvent::NewListenAddr { address, .. } => {
                            println!("{:?} Listening on {:?}", self.name, address);
                        },
                        SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            println!("{:?} Connected to {:?}", self.name, peer_id);
                        },
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            println!("{:?} Disconnected from {:?}", self.name, peer_id);
                        },

                        SwarmEvent::Behaviour(Event::Gossipsub(event)) => {
                            println!("GOSSIP {:?} {:?}", self.name, event);

                            match event {
                                gossipsub::Event::Message { propagation_source, message_id, message } => {
                                    println!("{:?} Received message '{:?}' from {:?} on {:?}", self.name, String::from_utf8_lossy(&message.data), propagation_source, message_id);
                                    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
                                    self.out_tx.clone().send(
                                    json!({
                                         "data": String::from_utf8_lossy(&message.data),
                                         "timestamp": SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_millis(),
                                         "event": "onMessage",
                                         "id": message_id.to_string(),
                                         "peer": propagation_source.to_string()
                                    }).to_string().as_bytes().to_vec()
                                ).await.unwrap();
                                // match self.broadcast(format!("Hi from {:?} at {:?}", self.name,SystemTime::now()  ).as_bytes()){
                                //         Ok(id) => {
                                //             println!("{:?} Broadcasted message  on {:?}", self.name, id);
                                //         }
                                //         Err(e) => {
                                //             println!("{:?} Failed to broadcast message on {:?}", self.name, e);
                                //         }
                                // };
                                },

                                gossipsub::Event::Subscribed { peer_id, topic } => {
                                    println!("{:?} Subscribed to topic {:?}", self.name, topic.clone().into_string());
                                    self.subscribed_topics.push(topic.into_string());
                                    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
                                  self.out_tx.clone().send(
                                    json!({
                                         "data": "Subscribed",
                                         "timestamp": SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_millis(),
                                         "event": "onSubscribed",
                                         "peer": "self"
                                    }).to_string().as_bytes().to_vec()
                                ).await.unwrap();
                                //     match self.broadcast( format!("Hi from {:?} at {:?}", self.name,SystemTime::now()  ).as_bytes() ){
                                //         Ok(id) => {
                                //             println!("{:?} Broadcasted message  on {:?}", self.name, id);
                                //         }
                                //         Err(e) => {
                                //             println!("{:?} Failed to broadcast message on {:?}", self.name, e);
                                //         }
                                // };
                                },

                                _ => {
                                 println!( "{:?}gossip WILD CARD {:?}", self.name, event);
                            }
                            }
                        },

                        SwarmEvent::Behaviour(Event::Mdns(event)) => {
                            println!("MDNS {:?} {:?}", self.name, event);

                            match event {
                                mdns::Event::Discovered(list) => {
                                    for (peer_id, _) in list {
                                        self.swarm.behaviour_mut().gossipsub.add_explicit_peer(&peer_id);
                                    }
                                },

                                mdns::Event::Expired(list) => {
                                    for (peer_id, _) in list {
                                        self.swarm.behaviour_mut().gossipsub.remove_explicit_peer(&peer_id);
                                    }
                                },
                            }
                        },
                        _ => {
                           println!( "WILD CARD");
                    }, // Wildcard pattern to cover all other cases
                }
            }
        }
    }
}

pub fn create_node(
    name: String,
    is_leader: bool,
    in_rx: mpsc::Receiver<Vec<u8>>,
) -> (Node, mpsc::Receiver<Vec<u8>>) {
    let swarm = SwarmBuilder::with_new_identity()
        .with_tokio()
        .with_tcp(
            Default::default(),
            libp2p::tls::Config::new,
            libp2p::yamux::Config::default,
        )
        .unwrap()
        // .with_quic()
        // .with_behaviour(|| NodeBehaviour {})
        .with_behaviour(|key| {
            let message_id_fn = |message: &gossipsub::Message| {
                let mut s = DefaultHasher::new();
                message.data.hash(&mut s);
                gossipsub::MessageId::from(s.finish().to_string())
            };

            // Set a custom gossipsub configuration
            let gossipsub_config = gossipsub::ConfigBuilder::default()
                .heartbeat_interval(Duration::from_secs(10)) // This is set to aid debugging by not cluttering the log space
                .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
                .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
                .build()
                .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))?; // Temporary hack because `build` does not return a proper `std::error::Error`.

            // build a gossipsub network behaviour
            let gossipsub = gossipsub::Behaviour::new(
                gossipsub::MessageAuthenticity::Signed(key.clone()),
                gossipsub_config,
            )?;

            let mdns =
                mdns::tokio::Behaviour::new(mdns::Config::default(), key.public().to_peer_id())?;
            Ok(NodeBehaviour { gossipsub, mdns })
        })
        .unwrap()
        .build();

    let (out_tx, _rx) = mpsc::channel(100);

    (
        Node {
            name,
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
    use std::hash::Hash;
    use serde_json::json;

    use crate::node::node::create_node;

    #[test]
    fn test_ping() {
        let port_id = 8888;
        let topic = "test_topic";

        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        let (tx_1, mut rx_1) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        let (mut node_0, mut rx_o_0) = create_node("node_0".to_string(), true, rx_0);
        let (mut node_1, mut rx_o_1) = create_node("node_1".to_string(), false, rx_1);

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();

        runtime.spawn(async move {
            node_0.connect(port_id, topic);
            node_0.run().await;
        });

        runtime.spawn(async move {
            while let Some(message) = rx_o_0.recv().await {
                println!("Node_0 Received: {}", String::from_utf8_lossy(&message));
                tx_0.send(json!({
                    "data": "Hi from Node_1",
                }).to_string().as_bytes().to_vec()).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
        });

        runtime.spawn(async move {
            while let Some(message) = rx_o_1.recv().await {
                println!("Node_1 Received: {}", String::from_utf8_lossy(&message));
                tx_1.send(json!({
                    "data": "Hi from Node_2",
                }).to_string().as_bytes().to_vec()).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
        });

        runtime.block_on(async move {
            // wait for 1 event to make sure swarm0 is listening
            tokio::time::sleep(std::time::Duration::from_millis(100)).await;

            node_1.connect(port_id, topic);
            node_1.run().await;
        });
    }
}
