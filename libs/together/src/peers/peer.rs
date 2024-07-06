use std::hash::{DefaultHasher, Hash, Hasher};
use std::str::FromStr;
use std::time::Duration;
use futures::StreamExt;
use libp2p::{gossipsub, identify, mdns, Multiaddr, noise, PeerId, ping, relay, Swarm, SwarmBuilder, tcp, tls, yamux};
use libp2p::core::muxing::StreamMuxerBox;
use libp2p::core::transport::dummy::DummyTransport;
use libp2p::swarm::{NetworkBehaviour, SwarmEvent};
use tokio::{io, select};

#[derive(NetworkBehaviour)]
// #[behaviour(to_swarm = "Event")]
struct PeerBehaviour {
    relay: relay::Behaviour,
    ping: ping::Behaviour,
    identify: identify::Behaviour,
    gossip_sub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
}

enum Event {
    GossipSub(gossipsub::Event),
    Mdns(mdns::Event),
    Ping(ping::Event),
    Identify(identify::Event),
    Relay(relay::Event),
}


impl PeerBehaviour {
    fn new(key: &libp2p::identity::Keypair) -> Self {
        let message_id_fn = |message: &gossipsub::Message| {
            let mut s = DefaultHasher::new();
            message.data.hash(&mut s);
            gossipsub::MessageId::from(s.finish().to_string())
        };

        // Set a custom Gossipsub configuration
        let gossip_sub_config = gossipsub::ConfigBuilder::default()
            .history_length(10)
            .history_gossip(10)
            .heartbeat_interval(Duration::from_secs(1)) // This is set to aid debugging by not cluttering the log space
            .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
            .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
            .build()
            .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
            .unwrap(); // Temporary hack because `build` does not return a proper `std::error::Error`.

        // build a Gossipsub network behaviour
        let gossip_sub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(key.clone()),
            gossip_sub_config,
        ).unwrap();

        Self {
            gossip_sub,
            mdns: mdns::tokio::Behaviour::new(mdns::Config::default(), key.public().to_peer_id())
                .unwrap(),
            relay: relay::Behaviour::new(key.public().to_peer_id(), Default::default()),
            ping: ping::Behaviour::new(ping::Config::new()),
            identify: identify::Behaviour::new(identify::Config::new(
                "/TODO/0.0.1".to_string(),
                key.public(),
            )),
        }
    }
}

async fn create_swarm() -> Swarm<PeerBehaviour> {
    SwarmBuilder::with_new_identity()
        .with_tokio()
        .with_tcp(
            tcp::Config::default(),
            noise::Config::new,
            yamux::Config::default,
        ).unwrap()
        .with_quic()
        .with_other_transport(|_key| DummyTransport::<(PeerId, StreamMuxerBox)>::new())
        .unwrap()
        .with_dns()
        .unwrap()
        .with_websocket(
            (tls::Config::new, noise::Config::new),
            yamux::Config::default,
        )
        .await
        .unwrap()
        .with_relay_client(
            (tls::Config::new, noise::Config::new),
            yamux::Config::default,
        )
        .unwrap()
        .with_behaviour(|_key, relay| {
            Ok(PeerBehaviour::new(_key))
        })
        .unwrap()
        .with_swarm_config(|cfg| {
            // Edit cfg here.
            cfg
                .with_idle_connection_timeout(Duration::from_secs(240))
        })
        .build()
}

pub async fn create_peer() {
    let mut swarm = create_swarm().await;

    swarm.listen_on(
        Multiaddr::from_str("/ip4/0.0.0.0/udp/0/quic-v1").unwrap()
    ).expect("TODO: panic message");

    loop {
        select! {
             event = swarm.select_next_some() => match event {
                 SwarmEvent::NewListenAddr { address, .. } => {
                    println!("{:?} NewListenAddr {:?}", swarm.local_peer_id(), address);
                 }
                 _ => {
                    println!("WILD CARD");
                }
             }
        }
    }
}