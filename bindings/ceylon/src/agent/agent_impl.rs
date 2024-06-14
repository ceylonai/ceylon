use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::SystemTime;


use tokio::select;
use tokio::sync::Mutex;
use uniffi::deps::log::debug;

use sangedama::node::node::{create_node, EventType, Message, MessageType};

use crate::agent::agent_base::{AgentConfig, AgentDefinition, MessageHandler, Processor};
use crate::agent::agent_context::{AgentContextManager};

pub struct AgentCore {
    _definition: RwLock<AgentDefinition>,
    _id: RwLock<Option<String>>,
    _workspace_id: RwLock<Option<String>>,
    _processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    tx_0: tokio::sync::mpsc::Sender<Message>,
    _meta: HashMap<String, String>,
    _event_handlers: HashMap<EventType, Vec<Arc<dyn MessageHandler>>>,

    _context_mgt: Arc<Mutex<AgentContextManager>>,
    _context_mgt_rx: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    _context_mgt_tx: tokio::sync::mpsc::Sender<Message>,
}

impl AgentCore {
    pub fn new(
        definition: AgentDefinition,
        config: AgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Option<Arc<dyn Processor>>,
        meta: Option<HashMap<String, String>>,
        event_handlers: Option<HashMap<EventType, Vec<Arc<dyn MessageHandler>>>>,
    ) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (_context_mgt_tx, _context_mgt_rx) = tokio::sync::mpsc::channel::<Message>(100);
        let mut _meta = meta.unwrap_or_default();

        let name = definition.name.clone();
        let is_leader = definition.is_leader;
        let position = definition.position.clone();
        let responsibilities = definition.responsibilities.clone();
        let instructions = definition.instructions.clone();

        _meta.insert("name".to_string(), name.clone());
        _meta.insert("is_leader".to_string(), is_leader.to_string());
        _meta.insert("position".to_string(), position.clone());
        _meta.insert("responsibilities".to_string(), responsibilities.join(","));
        _meta.insert("instructions".to_string(), instructions.join(","));
        _meta.insert(
            "created_at".to_string(),
            SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_millis()
                .to_string(),
        );

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

            _context_mgt: Arc::new(Mutex::new(AgentContextManager::new(config.memory_context_size))),
            _context_mgt_rx: Arc::new(Mutex::new(_context_mgt_rx)),
            _context_mgt_tx,
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
        let msg = Message::data(
            self.definition().id.clone().unwrap().clone(),
            to,
            message
        );
        Self::broadcast_raw(self._context_mgt_tx.clone(), self.tx_0.clone(), msg).await;
    }

    async fn broadcast_raw(context_mgt_tx: tokio::sync::mpsc::Sender<Message>, tx_0: tokio::sync::mpsc::Sender<Message>, message: Message) {
        context_mgt_tx.send(message.clone()).await.unwrap();
        tx_0
            .send(message)
            .await
            .unwrap();
    }

    pub fn meta(&self) -> HashMap<String, String> {
        self._meta.clone()
    }
}


impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition();
        let agent_name = definition.name.clone();
        let agent_id = self.id();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();
        let event_handlers = self._event_handlers.clone();

        self._id.write().unwrap().replace(agent_id.clone());
        self._definition.write().unwrap().id = Some(agent_id.clone());
        self._context_mgt.clone().lock().await.update_self_definition(self.definition());

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

                        if message.r#type != MessageType::Event{
                            ctx_tx.send(message.clone()).await.unwrap();
                        }

                        if message.r#type == MessageType::Message {
                             on_message.lock().await.on_message(agent_name.clone(), message.clone()).await;
                        }else if message.r#type == MessageType::Event {
                            for handler_event in event_handlers.keys() {
                                if handler_event == &message.event_type || handler_event == &EventType::OnAny {
                                    let handlers = event_handlers.get(handler_event).unwrap();
                                     for handler in handlers {
                                        let _messaage = message.clone();
                                        let _handler = handler.clone();
                                        let _name =  agent_name.clone();
                                        tokio::spawn(async move{
                                            _handler.on_message(_name, _messaage).await;
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
                select! {
                    Some(message) = rx.recv() => {
                       if let Some(msg) = ctx.add_message(message.clone()) {
                           Self::broadcast_raw(_context_mgt_tx.clone(), _tx_0.clone(), msg.clone()).await;
                       }
                    }
                }
            }
        });

        t0.await.unwrap();
        t1.await.unwrap();
        t2.await.unwrap();
        t3.await.unwrap();
    }
}
