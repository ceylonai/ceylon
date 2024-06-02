use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::{Duration, SystemTime};

use libp2p::{
    futures::StreamExt,
    gossipsub, mdns,
    swarm::{NetworkBehaviour, Swarm, SwarmEvent},
    Multiaddr, SwarmBuilder,
};
use libp2p_gossipsub::{MessageId, PublishError};
use tokio::{io, select};

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

struct Node {
    name: String,
    swarm: Swarm<NodeBehaviour>,
    is_leader: bool,
    subscribed_topics: Vec<String>,
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

    async fn run(mut self) {
        loop {
            select! {
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
                                match self.broadcast(format!("Hi from {:?} at {:?}", self.name,SystemTime::now()  ).as_bytes()){
                                        Ok(id) => {
                                            println!("{:?} Broadcasted message  on {:?}", self.name, id);
                                        }
                                        Err(e) => {
                                            println!("{:?} Failed to broadcast message on {:?}", self.name, e);
                                        }
                                };
                                },

                                gossipsub::Event::Subscribed { peer_id, topic } => {
                                    println!("{:?} Subscribed to topic {:?}", self.name, topic.clone().into_string());
                                    self.subscribed_topics.push(topic.into_string());

                                    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
                                    match self.broadcast( format!("Hi from {:?} at {:?}", self.name,SystemTime::now()  ).as_bytes() ){
                                        Ok(id) => {
                                            println!("{:?} Broadcasted message  on {:?}", self.name, id);
                                        }
                                        Err(e) => {
                                            println!("{:?} Failed to broadcast message on {:?}", self.name, e);
                                        }
                                };
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
                           println!( "{:?} WILD CARD", self.name);
                    }, // Wildcard pattern to cover all other cases
                }
            }
        }
    }
}

fn create_node(name: String, is_leader: bool) -> Node {
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
    Node {
        name,
        swarm,
        is_leader,
        subscribed_topics: Vec::new(),
    }
}

// Create test
#[cfg(test)]
mod tests {
    use std::hash::Hash;

    use crate::connect::node::create_node;

    #[test]
    fn test_ping() {
        let port_id = 8888;
        let topic = "test_topic";
        let mut node_0 = create_node("node_0".to_string(), true);
        let mut node_1 = create_node("node_1".to_string(), false);

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();

        runtime.spawn(async move {
            node_0.connect(port_id, topic);
            node_0.run().await;
        });

        runtime.block_on(async move {
            // wait for 1 event to make sure swarm0 is listening
            tokio::time::sleep(std::time::Duration::from_millis(100)).await;

            node_1.connect(port_id, topic);
            node_1.run().await;
        });
    }
}
