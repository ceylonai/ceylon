use log::{debug, info, error};
use pyo3::{IntoPy, Python};
use pyo3_asyncio::TaskLocals;

use crate::executor::{execute_process_function, execute_process_function_only};
use crate::transport::Transporter;
use crate::types::{Event, EventProcessor, EventType, FunctionInfo, OriginatorType, TransportStatus};

pub struct Application {
    name: String,
    event_processors: Vec<EventProcessor>,
    task_locals: Option<TaskLocals>,
    msg_server_rx: tokio::sync::watch::Receiver<String>,
    startup_handler: Option<FunctionInfo>,
    shutdown_handler: Option<FunctionInfo>,
}

pub struct FunctionExecutor {
    function: FunctionInfo,
    locals: TaskLocals,
}

impl FunctionExecutor {
    pub async fn execute(&mut self) {
        let task_locals_copy = self.locals.clone();
        let function = self.function.clone();
        match execute_process_function_only(&function, &task_locals_copy)
            .await
        {
            Ok(_) => (debug!("Server starting..."), ),
            Err(e) => (error!("Error on processing message {:?}", e), )
        };
    }
}

impl Application {
    pub fn new(name: &str, msg_rx: tokio::sync::watch::Receiver<String>) -> Self {
        Self {
            name: name.to_string(),
            event_processors: Vec::new(),
            task_locals: None,
            msg_server_rx: msg_rx,
            startup_handler: None,
            shutdown_handler: None,
        }
    }

    pub fn boot(&mut self) -> FunctionExecutor {
        return FunctionExecutor {
            function: self.startup_handler.clone().unwrap(),
            locals: self.task_locals.clone().unwrap(),
        };
    }

    pub fn shutdown(&mut self) -> FunctionExecutor {
        return FunctionExecutor {
            function: self.shutdown_handler.clone().unwrap(),
            locals: self.task_locals.clone().unwrap(),
        };
    }

    pub async fn start<T: Transporter>(&mut self) {
        info!("Starting application: {}", self.name);
        let task_locals_copy = self.task_locals.clone().unwrap();
        let message_handlers = self.event_processors.clone();

        let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        let mut msg_porter = T::new(tx.clone(), self.name.clone());
        let tx = msg_porter.get_tx();

        let mut msg_server_rx = self.msg_server_rx.clone();
        tokio::spawn(async move {
            loop {
                tokio::select! {
                    msg = msg_server_rx.changed() => {
                        match msg {
                    Ok(_msg) => {
                        let data = msg_server_rx.borrow().to_string();
                        debug!("Server->Application: {}", data.clone());
                        match tx.send(data).await {
                            Ok(_) => {
                                debug!("Sent message");
                            }
                            Err(e) => {
                                error!("Error on sending message at Server->Application (49) {}", e);
                            }
                        }
                    }
                    Err(e) => {
                       error!("Error on sending message at Server->Application (54) {}", e);
                    }
                }
                    }
                }
            }
        });

        let message_processors = self.event_processors.clone();
        tokio::spawn(async move {
            let _mh = message_handlers.clone();
            while let Some(tr_status) = rx.recv().await {
                let event = if let TransportStatus::Data(message) = tr_status {
                    Event::new(message.data, EventType::Data, message.sender,
                               message.sender_id,
                               OriginatorType::Agent)
                } else {
                    let (msg, status) = match tr_status {
                        TransportStatus::Data(data) => (data.sender, EventType::Data),
                        TransportStatus::Error(err) => (err, EventType::Error),
                        TransportStatus::Info(info) => (info, EventType::Message),
                        TransportStatus::PeerDiscovered(peer_id) => (peer_id, EventType::SystemEvent),
                        TransportStatus::PeerConnected(peer_id) => (peer_id, EventType::SystemEvent),
                        TransportStatus::PeerDisconnected(peer_id) => (peer_id, EventType::SystemEvent),
                        TransportStatus::Stopped => ("Stopped".to_string(), EventType::Stop),
                        TransportStatus::Started => ("Ready".to_string(), EventType::Start),
                    };
                    Event::new(msg, status,
                               "SYSTEM".to_string(),
                               "SYSTEM".to_string(),
                               OriginatorType::System)
                };

                let input = Python::with_gil(|py| event.clone().into_py(py));
                let mut threads = Vec::new();
                for mp in message_processors.iter() {
                    // println!("Processing message {:?}, {:?} , {:?}", event.event_type, mp.event, mp.event != event.event_type);
                    if mp.event != event.event_type { continue; }
                    // info!("Processing message {:?}, {:?} , {:?} {} - {}", event.event_type, mp.event, mp.event != event.event_type, event.creator_id, mp.owner_id);
                    let input_copy = input.clone();
                    let tlc = task_locals_copy.clone();
                    let mp2 = mp.clone();
                    let t1 = tokio::spawn(async move {
                        match execute_process_function(input_copy.clone(), &mp2.function, &tlc)
                            .await
                        {
                            Ok(_) => (debug!("Server starting..."), ),
                            Err(e) => (error!("Error on processing message {:?}", e), )
                        };
                    });
                    threads.push(t1);
                }
                for t in threads {
                    debug!("Waiting for thread");
                    t.await.unwrap();
                }
                debug!("Processing message released");
            }
        });

        match msg_porter.message_processor().await {
            Ok(_) => {
                info!("Message Porter started");
            }
            Err(e) => {
                error!("Message Porter failed to start{:?}", e);
            }
        };
    }

    pub fn initialize(&mut self, task_local: TaskLocals) {
        self.task_locals = Some(task_local);
    }

    pub fn add_startup_handler(&mut self, mp: FunctionInfo) {
        self.startup_handler = Some(mp);
    }
    pub fn add_shutdown_handler(&mut self, mp: FunctionInfo) {
        self.shutdown_handler = Some(mp);
    }

    pub fn add_event_processor(&mut self, mp: EventProcessor) {
        self.event_processors.push(mp);
    }
    pub fn remove_message_handler(&mut self, mp: EventProcessor) {
        for i in 0..self.event_processors.len() {
            if self.event_processors[i].name == mp.name {
                self.event_processors.remove(i);
                break;
            }
        }
    }
}
