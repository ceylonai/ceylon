use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;

use futures::StreamExt;
use libp2p::{gossipsub, mdns, Multiaddr, Swarm, SwarmBuilder};
use libp2p::swarm::NetworkBehaviour;
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

struct RunnerConfig {
    topic_name: &'static str,
    is_leader: bool,
    url: &'static str,
}

impl RunnerConfig {
    pub fn new(topic_name: &'static str, is_leader: bool, url: &'static str) -> Self {
        Self {
            topic_name,
            is_leader,
            url,
        }
    }
}

struct Message {
    data: Vec<u8>,
}

pub async fn node_runner(config: RunnerConfig, mut rx: tokio::sync::mpsc::Receiver<Message>) {
    let mut swarm = create_swarm();
    let peer_id = swarm.local_peer_id();
    // Create a Gossipsub topic
    let topic = gossipsub::IdentTopic::new(config.topic_name);

    let is_leader = config.is_leader;
    let url = config.url;


    // {
    //     let swarm_ref = swarm.as_ref();
    //     &swarm_ref
    //         .behaviour_mut()
    //         .gossipsub
    //         .subscribe(&topic)
    //         .unwrap();
    //     if is_leader {
    //         swarm_ref
    //             .listen_on(url.parse().unwrap())
    //             .unwrap();
    //     } else {
    //         swarm_ref
    //             .dial(
    //                 url
    //                     .parse::<Multiaddr>()
    //                     .unwrap(),
    //             )
    //             .unwrap();
    //     }
    // }

    

    loop {
        if let Some(message) = rx.recv().await {
            println!("{:?} Received message '{:?}' ", peer_id, String::from_utf8_lossy(&message.data));
        }
    }
}

fn connect_swarm(mut swarm: Swarm<NodeBehaviour>, topic: gossipsub::IdentTopic, is_leader: bool, port: u16) {
    swarm
        .behaviour_mut()
        .gossipsub
        .subscribe(&topic)
        .unwrap();
    if is_leader {
        swarm
            .listen_on(format!("/ip4/0.0.0.0/tcp/{}", port).parse().unwrap())
            .unwrap();
    } else {
        swarm
            .dial(
                format!("/ip4/0.0.0.0/tcp/{}", port)
                    .parse::<Multiaddr>()
                    .unwrap(),
            )
            .unwrap();
    }
}

fn create_swarm() -> Box<Swarm<NodeBehaviour>> {
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

    Box::new(swarm)
}

#[cfg(test)]
mod tests {
    use std::time::{Duration, SystemTime};
    use log::info;

    use crate::node::node_runner::{Message, node_runner, RunnerConfig};

    #[test]
    fn test_ping() {
        env_logger::init();
        let topic = "test_topic";

        let config_1 = RunnerConfig::new(topic, true, "/ip4/0.0.0.0/tcp/8888");
        let config_2 = RunnerConfig::new(topic, false, "/ip4/0.0.0.0/tcp/8888");

        // let mut node_0 = crate::node::node::create_node("node_0".to_string(), true);
        // let mut node_1 = crate::node::node::create_node("node_1".to_string(), false);
        // 
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        // 

        let (tx, rx) = tokio::sync::mpsc::channel(10);
        runtime.spawn(async move {
            node_runner(config_1, rx).await;
        });

        // let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        // 
        // // Spawning the consumer task
        // runtime.spawn(async move {
        //     while let Some(message) = rx.recv().await {
        //         println!("Received: {}", message);
        //     }
        // });

        // Simulating multiple sender tasks
        // for i in 0..5 {
        //     let tx = tx.clone();
        //     runtime.spawn(async move {
        //         let msg = format!("Message from sender {}", i);
        //         tx.send(msg).await.unwrap();
        //         tokio::time::sleep(Duration::from_secs(1)).await;
        //     });
        // }
        runtime.block_on(async move {
            // wait for 1 event to make sure swarm0 is listening
            loop {
                tokio::time::sleep(Duration::from_millis(100)).await;
                println!("{:?}", SystemTime::now());
                tx.send(Message {
                    data: format!("Hi from {:?} at {:?}", "node_0", SystemTime::now()).as_bytes().to_vec(),
                }).await.unwrap();
            }
        });
        // 
        // runtime.block_on(async move {
        //     // wait for 1 event to make sure swarm0 is listening
        //     tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        // 
        //     node_1.connect(port_id, topic);
        //     node_1.run().await;
        // });
    }
}