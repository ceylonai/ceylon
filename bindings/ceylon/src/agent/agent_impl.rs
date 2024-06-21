use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, UNIX_EPOCH};

use tokio::select;
use tokio::sync::Mutex;
use uniffi::deps::log::{debug, info, Level, log};

use sangedama::node::node::{create_node, EventType, Message, MessageType};

use crate::agent::agent_base::{
    AgentConfig, AgentDefinition, AgentHandler, MessageHandler, Processor,
};
use crate::agent::agent_context::AgentContextManager;
use crate::agent::message_types::{
    AgentMessage, AgentMessageConversions, AgentMessageTrait, AgentMessageType, BeaconMessage,
    DataMessage, HandshakeMessage, IntroduceMessage,
};
use crate::EventHandler;

pub struct AgentCore {
    _definition: RwLock<AgentDefinition>,
    _id: RwLock<Option<String>>,
    _workspace_id: RwLock<Option<String>>,
    _processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    _agent_handler: Arc<Mutex<Arc<dyn AgentHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    tx_0: tokio::sync::mpsc::Sender<Message>,
    _meta: HashMap<String, String>,
    _event_handlers: HashMap<EventType, Vec<Arc<dyn EventHandler>>>,

    _context_mgt: Arc<Mutex<AgentContextManager>>,
    _context_mgt_rx: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    _context_mgt_tx: tokio::sync::mpsc::Sender<Message>,
}

impl AgentCore {
    pub fn new(
        mut definition: AgentDefinition,
        config: AgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Option<Arc<dyn Processor>>,
        meta: Option<HashMap<String, String>>,
        agent_handler: Arc<dyn AgentHandler>,
        event_handlers: Option<HashMap<EventType, Vec<Arc<dyn EventHandler>>>>,
    ) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (_context_mgt_tx, _context_mgt_rx) = tokio::sync::mpsc::channel::<Message>(100);
        let mut _meta = meta.unwrap_or_default();
        Self {
            _id: RwLock::new(None),
            _workspace_id: RwLock::new(None),
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            rx_0: Arc::new(Mutex::new(rx_0)),
            tx_0,
            _meta,
            _definition: RwLock::new(definition),
            _event_handlers: event_handlers.unwrap_or_default(),
            _context_mgt: Arc::new(Mutex::new(AgentContextManager::new(
                config.memory_context_size,
            ))),
            _context_mgt_rx: Arc::new(Mutex::new(_context_mgt_rx)),
            _context_mgt_tx,
            _agent_handler: Arc::new(Mutex::new(agent_handler)),
        }
    }

    pub fn definition(&self) -> AgentDefinition {
        self._definition.read().unwrap().clone()
    }

    pub fn id(&self) -> String {
        self._id.read().unwrap().clone().unwrap_or("".to_string())
    }

    pub fn workspace_id(&self) -> String {
        self._workspace_id
            .read()
            .unwrap()
            .clone()
            .unwrap_or("".to_string())
    }

    pub fn set_workspace_id(&self, workspace_id: String) {
        self._workspace_id.write().unwrap().replace(workspace_id);
    }

    pub async fn broadcast(&self, message: Vec<u8>, to: Option<String>) {
        let message =
            AgentMessage::from_data(AgentMessageType::Data, DataMessage { data: message })
                .into_bytes();
        info!("broadcasting message: {:?} to: {:?}", message, to);
        let msg = Message::data(self.definition().id.clone().unwrap().clone(), to, message);
        Self::broadcast_raw(self._context_mgt_tx.clone(), self.tx_0.clone(), msg).await;
    }

    async fn broadcast_raw(
        context_mgt_tx: tokio::sync::mpsc::Sender<Message>,
        tx_0: tokio::sync::mpsc::Sender<Message>,
        message: Message,
    ) {
        context_mgt_tx.send(message.clone()).await.unwrap();
        tx_0.send(message).await.unwrap();
    }

    pub fn meta(&self) -> HashMap<String, String> {
        self._meta.clone()
    }

    pub fn log(&self, message: String) {
        log!(Level::Info,"{}: {}", self.id(), message);
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition();
        let agent_name = definition.name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();
        let event_handlers = self._event_handlers.clone();
        let agent_handler = self._agent_handler.clone();
        let agent_id = node_0.id.clone();

        self._id.write().unwrap().replace(agent_id.clone());
        info!("{} - Agent {} Started", self.id().clone(), agent_name.clone());
        self._definition.write().unwrap().id = Some(agent_id.clone());
        self._context_mgt
            .clone()
            .lock()
            .await
            .set_self_definition(self.definition());


        let processor = self._processor.clone();
        if let Some(processor) = processor.lock().await.clone() {
            // Non blocking events on start
            processor.on_start(inputs.clone()).await;
        }
        let t0 = tokio::spawn(async move {
            node_0.connect(url.as_str(), topic.as_str());
            node_0.run().await;
        });

        let rx = Arc::clone(&self.rx_0);
        let ctx_tx = self._context_mgt_tx.clone();
        let t1 = tokio::spawn(async move {
            let mut rx = rx.lock().await;
            loop {
                select! {
                        Some(message) = rx.recv() => {
                            debug!("{} Received: {:?}", agent_name.clone(), message.clone());
                            tx_0.clone().send(message).await.unwrap();
                        }
                        Some(message) = rx_o_0.recv() => {

                        // self._context_mgt.write().unwrap().add_message(message.clone());


                        if message.r#type == MessageType::Message {
                            ctx_tx.send(message.clone()).await.unwrap();
                        }else if message.r#type == MessageType::Event {
                            for handler_event in event_handlers.keys() {
                                if handler_event == &message.event_type || handler_event == &EventType::OnAny {
                                    let handlers = event_handlers.get(handler_event).unwrap();
                                     for handler in handlers {
                                        let _messaage = message.clone();
                                        let _handler = handler.clone();
                                        let _name =  agent_name.clone();
                                        tokio::spawn(async move{
                                            _handler.on_event(_messaage).await;
                                        });
                                     }
                                };
                            }
                        }
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let t2 = tokio::spawn(async move {
            if let Some(processor) = processor.lock().await.clone() {
                processor.run(inputs).await;
            }
        });

        let _context_mgt_rx = Arc::clone(&self._context_mgt_rx);
        let _context_mgt = Arc::clone(&self._context_mgt);
        let _tx_0 = self.tx_0.clone();
        let _context_mgt_tx = self._context_mgt_tx.clone();
        let t3 = tokio::spawn(async move {
            let mut rx = _context_mgt_rx.lock().await;
            let mut ctx = _context_mgt.lock().await;
            loop {
                let message_creator = ctx.get_owner().id.unwrap_or("".to_string());
                select! {
                    Some(message) = rx.recv() => {
                        if message.sender == message_creator.clone()  {
                            ctx.add_message( message.clone());
                            continue;
                        }
                        let msg = AgentMessage::from_bytes(message.data.clone());
                        let sender_id = message.sender.clone();
                        
                        
                        debug!("{} Received: {:?}", message_creator.clone(), sender_id.clone());
                                                
                        if ctx.has_thread( sender_id) {
                            debug!("Received: {:?}",msg.clone());
                            if msg.r#type==AgentMessageType::Data {
                                let data_msg:Option<DataMessage> = msg.into_data();
                                if let Some(data_msg) = data_msg {
                                    on_message.lock().await.on_message(message.sender, data_msg.data).await;
                                }
                            }
                        }else{
                            debug!("No context for {}", message.sender);
                            
                            if msg.r#type==AgentMessageType::Handshake {
                                let handshake_msg:Option<HandshakeMessage> = msg.into_data();
                                debug!("{} Handshake received: {:?}",definition.name,handshake_msg);
                                let handshake_message = IntroduceMessage{
                                    agent_definition: ctx.get_owner().clone(),
                                };
                                AgentCore::broadcast_raw(_context_mgt_tx.clone(),_tx_0.clone(),
                                    Message::data(message_creator.clone(),None,
                                    AgentMessage::from_data(AgentMessageType::Introduce,
                                            handshake_message).into_bytes()) ).await;
                            }else if msg.r#type==AgentMessageType::Introduce {
                                let data_msg:Option<IntroduceMessage> = msg.into_data();
                                if let Some(data_msg) = data_msg {
                                    ctx.create_context(data_msg.agent_definition.clone());
                                    debug!( "{} has joined", ctx.has_thread( message.sender.clone()));
                                    agent_handler.lock().await.on_agent(data_msg.agent_definition ).await;
                                }

                            }
                        }
                    }
                }
            }
        });
        let message_creator = self.id().clone();
        let agent_name = self.definition().name.clone();
        let _context_mgt_tx = self._context_mgt_tx.clone();
        let _tx_0 = self.tx_0.clone();
        let t4 = tokio::spawn(async move {
            // Need to stop this after a while
            let mut sleep_duration = Duration::from_secs(1); // Initial sleep duration
            loop {
                let handshake_message = HandshakeMessage {
                    message: format!("Im a new agent {}", agent_name),
                };
                AgentCore::broadcast_raw(_context_mgt_tx.clone(), _tx_0.clone(),
                                         Message::data(message_creator.clone(), None,
                                                       AgentMessage::from_data(AgentMessageType::Handshake,
                                                                               handshake_message).into_bytes())).await;
                tokio::time::sleep(sleep_duration).await;
                sleep_duration += Duration::from_secs(1);
                // if sleep_duration > Duration::from_secs(120) {
                //     sleep_duration = Duration::from_secs(45);
                // }
            }
        });


        t0.await.unwrap();
        t1.await.unwrap();
        t2.await.unwrap();
        t3.await.unwrap();
        t4.await.unwrap();

        // select! {
        //     _ = t0 => {
        //         debug!("{} - Agent {} Stopped", self.id().clone(), "Processor");
        //     },
        //     _ = t1 => {
        //         debug!("{} - Agent {} Stopped", self.id().clone(), "Message Dispatcher");
        //     },
        //     _ = t2 => {
        //         debug!("{} - Agent {} Stopped", self.id().clone(), "Message Processor");
        //     },
        //     _ = t3 => {
        //         debug!("{} - Agent {} Stopped", self.id().clone(), "Memory Context handler");
        //     },
        //     _ = t4 => {
        //         debug!("{} - Agent {} Stopped", self.id().clone(), "Beacon");
        //     },
        // }
    }
}
