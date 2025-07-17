/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use crate::messaging::{AnpCodec, AnpRequest, AnpResponse};
use libp2p::mdns::tokio::Tokio;
use libp2p::{gossipsub, mdns::{Behaviour as Mdns, Event as MdnsEvent}, request_response::{Behaviour as RequestResponse, Event as RequestResponseEvent}, swarm::NetworkBehaviour};

pub type AgentRequestResponseBehaviour = RequestResponse<AnpCodec>;
/// Combines RequestResponse (for ANP) and mDNS discovery into a single behaviour.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "AgentEvent", event_process = false)]
pub struct AgentBehaviour {
    /// Handles ANP protocol messaging
    pub request_response: AgentRequestResponseBehaviour,

    /// mDNS for local peer discovery
    pub mdns: Mdns<Tokio>,

    pub ping: libp2p::ping::Behaviour,

    pub gossipsub: gossipsub::Behaviour
}

/// Unified event type for all AgentBehaviour events.
#[derive(Debug)]
pub enum AgentEvent {
    /// Events from RequestResponse (ANP messages)
    RequestResponse(RequestResponseEvent<AnpRequest, AnpResponse>),

    /// Events from mDNS discovery
    Mdns(MdnsEvent),

    /// Events from ping
    Ping(libp2p::ping::Event),

    GossipSub(gossipsub::Event)
}

impl From<libp2p::ping::Event> for AgentEvent {
    fn from(event: libp2p::ping::Event) -> Self {
        AgentEvent::Ping(event)
    }
}

impl From<gossipsub::Event> for AgentEvent {
    fn from(event: gossipsub::Event) -> Self {
        AgentEvent::GossipSub(event)
    }
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
