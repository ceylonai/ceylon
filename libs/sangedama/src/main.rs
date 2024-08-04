mod peer;

use std::net::Ipv4Addr;
use std::str::FromStr;

use libp2p::multiaddr::Protocol;
use libp2p::{Multiaddr, PeerId};
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::info;

use peer::message::data::NodeMessage;
use peer::node::{
    create_key, get_peer_id, AdminPeer, AdminPeerConfig, MemberPeer, MemberPeerConfig,
};

#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
    let workspace_id = "workspace-test".to_string();
    info!("Starting {}", workspace_id);

    let admin_port = 7845;
    let admin_config = AdminPeerConfig::new(admin_port, workspace_id.clone());
    let admin_key = create_key();
    let admin_id_from_key = get_peer_id(&admin_key);
    let (mut admin_peer, mut admin_listener) =
        AdminPeer::create(admin_config.clone(), admin_key).await;
    let admin_id = admin_peer.id.clone();

    let cancel_token = CancellationToken::new();

    if admin_id.to_string() == admin_id_from_key.to_string() {
        info!("Admin peer created with id: {}", admin_id);
    }

    let admin_emitter = admin_peer.emitter();
    let cancel_token_clone = cancel_token.clone();
    let task_admin = tokio::task::spawn(async move {
        admin_peer.run(None, cancel_token_clone).await;
    });

    let task_admin_listener = tokio::spawn(async move {
        loop {
            select! {
               event = admin_listener.recv() => {
                    if event.is_some() {
                        let event = event.unwrap();
                        match event{
                            NodeMessage::Message{ data,created_by, ..} => {
                                info!("Admin listener Message {:?} from {:?}",String::from_utf8(data),created_by);
                            }
                            _ => {
                                info!("peer1 listener {:?}", event);
                            }
                        }
                    }
                }
            }
        }
    });

    let task_run_admin = tokio::task::spawn(async move {
        loop {
            admin_emitter
                .send("Admin Send regards".to_string().as_bytes().to_vec())
                .await
                .unwrap();
            tokio::time::sleep(std::time::Duration::from_millis(1000)).await;
        }
    });

    // Here we create localhost address to connect peer with admin
    let peer_dial_address = Multiaddr::empty()
        .with(Protocol::Ip4(Ipv4Addr::LOCALHOST))
        .with(Protocol::Udp(admin_port))
        .with(Protocol::QuicV1);

    let peer_1 = create_client(
        workspace_id.clone(),
        admin_id.clone(),
        admin_port,
        peer_dial_address.clone(),
        "peer1".to_string(),
        cancel_token.clone(),
    )
    .await;
    let peer_2 = create_client(
        workspace_id.clone(),
        admin_id.clone(),
        admin_port,
        peer_dial_address.clone(),
        "peer2".to_string(),
        cancel_token.clone(),
    )
    .await;
    let peer_3 = create_client(
        workspace_id.clone(),
        admin_id.clone(),
        admin_port,
        peer_dial_address.clone(),
        "peer3".to_string(),
        cancel_token.clone(),
    )
    .await;
    let peer_4 = create_client(
        workspace_id.clone(),
        admin_id.clone(),
        admin_port,
        peer_dial_address.clone(),
        "peer4".to_string(),
        cancel_token.clone(),
    )
    .await;

    task_admin.await.unwrap();
    task_admin_listener.await.unwrap();
    task_run_admin.await.unwrap();

    peer_1.await.unwrap();
    peer_2.await.unwrap();
    peer_3.await.unwrap();
    peer_4.await.unwrap();
}

async fn create_client(
    workspace_id: String,
    admin_id: String,
    admin_port: u16,
    peer_dial_address: Multiaddr,
    name: String,
    cancel_token: CancellationToken,
) -> tokio::task::JoinHandle<()> {
    let member_key = create_key();
    let member_id_from_key = get_peer_id(&member_key);
    let (mut peer2, mut peer2_listener) = MemberPeer::create(
        MemberPeerConfig {
            name: name.clone(),
            workspace_id: workspace_id.clone(),
            admin_peer: PeerId::from_str(&admin_id).unwrap(),
            rendezvous_point_address: peer_dial_address.clone(),
        },
        member_key,
    )
    .await;

    let peer2_emitter = peer2.emitter();
    let peer2_id = peer2.id.clone();

    if member_id_from_key.to_string() == peer2_id.to_string() {
        info!("{} {} created", name.clone(), peer2_id);
    }
    let cancel_token_clone = cancel_token.clone();
    let task_peer_2 = tokio::task::spawn(async move {
        peer2.run(cancel_token_clone).await;
    });

    let name_clone = name.clone();
    let task_peer_2_listener = tokio::spawn(async move {
        loop {
            select! {
                event = peer2_listener.recv() => {
                  if event.is_some() {
                        let event = event.unwrap();
                        match event{
                            NodeMessage::Message{ data,created_by, ..} => {
                                info!("{} {} listener Message {:?} from {:?}",name.clone(),peer2_id, String::from_utf8(data),created_by);
                            }
                            _ => {
                                info!("{} listener {:?}",name.clone(), event);
                            }
                        }
                    }
                }
            }
        }
    });

    let task_run_peer_2 = tokio::task::spawn(async move {
        loop {
            peer2_emitter
                .send(
                    format!("{} Send regards", name_clone.clone())
                        .as_bytes()
                        .to_vec(),
                )
                .await
                .expect("TODO: panic message");
            tokio::time::sleep(std::time::Duration::from_millis(3000)).await;
        }
    });

    tokio::spawn(async {
        task_peer_2.await.unwrap();
        task_peer_2_listener.await.unwrap();
        task_run_peer_2.await.unwrap();
    })
}
