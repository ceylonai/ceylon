use std::sync::{Arc, Mutex};

use log::info;
use pyo3::{IntoPy, Python};
use pyo3_asyncio::TaskLocals;
use tokio::sync::mpsc::Receiver;

use crate::executor::{execute_event_handler, execute_process_function};
use crate::transport::Transporter;
use crate::types::{FunctionInfo, MessageProcessor};

pub(crate) struct Application {
    name: String,
    startup_handler: Option<Arc<FunctionInfo>>,
    shutdown_handler: Option<Arc<FunctionInfo>>,
    message_handlers: Vec<MessageProcessor>,
    background_process_handler: Option<Arc<FunctionInfo>>,
    task_locals: Option<TaskLocals>,
    msg_rx: tokio::sync::watch::Receiver<String>,
}

impl Application {
    pub fn new(name: &str, msg_rx: tokio::sync::watch::Receiver<String>) -> Self {
        Self {
            name: name.to_string(),
            startup_handler: None,
            shutdown_handler: None,
            background_process_handler: None,
            message_handlers: Vec::new(),
            task_locals: None,
            msg_rx,
        }
    }
    // pub fn dispatch(&mut self, message: &str) {
    //     println!("Received message: {}", message);
    //     self.msg_tx.send(message.to_string()).unwrap();
    // }

    pub async fn start(&mut self) {
        println!("Starting application: {}", self.name);
        let mut task_locals_copy = self.task_locals.clone().unwrap();
        let mut task_locals_bg = self.task_locals.clone().unwrap();
        let mut task_locals_copy2 = self.task_locals.clone().unwrap();
        let startup_handler = self.startup_handler.clone();
        let background_processor = self.background_process_handler.clone();
        let message_handlers = self.message_handlers.clone();


        match execute_event_handler(startup_handler, &task_locals_copy)
            .await {
            Ok(_) => (
                info!("Server starting..."),
            ),
            Err(e) => (
                println!("error 11 {}", e),
            )
        };

        let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        let mut msg_porter = Transporter::new(tx.clone(), self.name.clone());
        let tx = msg_porter.get_tx();

        let mut rxt = self.msg_rx.clone();
        tokio::spawn(async move {
            while let msg = rxt.changed().await {
                match msg {
                    Ok(msg) => {
                        let data = rxt.borrow().to_string();
                        match tx.send(data).await {
                            Ok(_) => {
                                info!("Sent message");
                            }
                            Err(e) => {
                                println!("error 33 {}", e);
                            }
                        }
                    }
                    Err(e) => {
                        println!("error 44 {}", e);
                    }
                }
            }
        });

        let message_processors = self.message_handlers.clone();
        tokio::spawn(async move {
            let mh = message_handlers.clone();
            while let Some(message) = rx.recv().await {
                // println!("Received message: {:?}", message.clone());

                let input = Python::with_gil(|py| {
                    message.clone().into_py(py)
                });

                for mp in message_processors.iter() {
                    let input_copy = input.clone();
                    let tlc = task_locals_copy.clone();
                    let mp2 = mp.clone();
                    tokio::spawn(async move {
                        match execute_process_function(input_copy.clone(), &mp2.function, &tlc).await {
                            Ok(_) => (
                                info!("Server starting..."),
                            ),
                            Err(e) => (
                                println!("error 55 {}", e),
                            )
                        };
                    });
                }
            }
        });

        match msg_porter.message_processor().await {
            Ok(_) => {
                info!("Message Porter started");
            }
            Err(e) => {
                println!("Message Porter error 66 {}", e);
            }
        };
    }

    pub fn initialize(&mut self, task_local: TaskLocals) {
        self.task_locals = Some(task_local);
    }

    pub fn shutdown(&mut self) {}

    pub fn set_startup_handler(&mut self, handler: FunctionInfo) {
        self.startup_handler = Some(Arc::new(handler));
    }

    pub fn set_shutdown_handler(&mut self, handler: FunctionInfo) {
        self.shutdown_handler = Some(Arc::new(handler));
    }

    pub fn set_background_processor(&mut self, handler: FunctionInfo) {
        self.background_process_handler = Some(Arc::new(handler));
    }

    pub fn add_message_handler(&mut self, mp: MessageProcessor) {
        self.message_handlers.push(mp);
    }
}