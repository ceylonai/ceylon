use std::net::Ipv4Addr;
use std::time::Duration;

use futures::StreamExt;
use libp2p::{autonat, identify, identity, noise, PeerId, tcp, yamux};
use libp2p::core::{Multiaddr, multiaddr::Protocol};
use libp2p::swarm::{NetworkBehaviour, SwarmEvent};
use tokio::select;
use tokio::task::JoinHandle;
use tracing::info;
use tracing_subscriber::EnvFilter;

#[derive(Debug)]
pub struct PeerAdminConfig {
    listen_port: Option<u16>,
}

impl PeerAdminConfig {
    pub fn new(listen_port: u16) -> Self {
        Self { listen_port: Some(listen_port) }
    }
}

pub async fn create_server(opt: PeerAdminConfig) -> (JoinHandle<()>, PeerId) {
    let key = identity::Keypair::generate_ed25519();
    let mut swarm = libp2p::SwarmBuilder::with_existing_identity(key)
        .with_tokio()
        .with_tcp(
            tcp::Config::default(),
            noise::Config::new,
            yamux::Config::default,
        )
        .unwrap()
        .with_behaviour(|key| Behaviour::new(key.public()))
        .unwrap()
        .with_swarm_config(|c| c.with_idle_connection_timeout(Duration::from_secs(60)))
        .build();

    swarm.listen_on(
        Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Tcp(opt.listen_port.unwrap_or(0))),
    );
    let peer_id = swarm.local_peer_id().clone();


    tracing::info!( "Local peer id Admin: {:?}", peer_id.clone());

    let server_task = tokio::task::spawn(async move {
        loop {
            select! {
                event = swarm.select_next_some() => match event {
                    SwarmEvent::NewListenAddr { address, .. } => info!("Listening on {address:?}"),
                    _ => {
                        info!("WILD CARD Server {:?}", event);
                    }
                }
            }

            match swarm.select_next_some().await {
                SwarmEvent::NewListenAddr { address, .. } => info!("Listening on {address:?}"),
                SwarmEvent::Behaviour(event) => info!("{event:?}"),
                e => info!("{e:?}"),
            }
        }
    });

    (server_task, peer_id)
}

#[derive(NetworkBehaviour)]
struct Behaviour {
    identify: identify::Behaviour,
    auto_nat: autonat::Behaviour,
}

impl Behaviour {
    fn new(local_public_key: identity::PublicKey) -> Self {
        Self {
            identify: identify::Behaviour::new(identify::Config::new(
                "/ipfs/0.1.0".into(),
                local_public_key.clone(),
            )),
            auto_nat: autonat::Behaviour::new(
                local_public_key.to_peer_id(),
                autonat::Config {
                    only_global_ips: false,
                    ..Default::default()
                },
            ),
        }
    }
}