use crate::messaging::{AnpCodec, AnpRequest, AnpResponse};
use libp2p::mdns::tokio::Tokio;
use libp2p::{
    PeerId,
    mdns::{Behaviour as Mdns, Event as MdnsEvent},
    request_response::{Behaviour as RequestResponse, Event as RequestResponseEvent},
    swarm::NetworkBehaviour,
};

/// Combines RequestResponse (for ANP) and mDNS discovery into a single behaviour.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "AgentEvent", event_process = false)]
pub struct AgentBehaviour {
    /// Handles ANP protocol messaging
    pub request_response: RequestResponse<AnpCodec>,

    /// mDNS for local peer discovery
    pub mdns: Mdns<Tokio>,
}

/// Unified event type for all AgentBehaviour events.
#[derive(Debug)]
pub enum AgentEvent {
    /// Events from RequestResponse (ANP messages)
    RequestResponse(RequestResponseEvent<AnpRequest, AnpResponse>),

    /// Events from mDNS discovery
    Mdns(MdnsEvent),
}

// Conversion glue so libp2p can turn sub-behaviour events into our top-level AgentEvent
impl From<RequestResponseEvent<AnpRequest, AnpResponse>> for AgentEvent {
    fn from(event: RequestResponseEvent<AnpRequest, AnpResponse>) -> Self {
        AgentEvent::RequestResponse(event)
    }
}

impl From<MdnsEvent> for AgentEvent {
    fn from(event: MdnsEvent) -> Self {
        AgentEvent::Mdns(event)
    }
}
