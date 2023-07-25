use std::sync::{Arc};
use log::info;
use pyo3::{IntoPy, Python};


use pyo3_asyncio::TaskLocals;

use crate::executor::{execute_event_handler, execute_process_function};
use crate::transport::Transporter;
use crate::types::{FunctionInfo, MessageProcessor};

pub(crate) struct Application {
    name: String,
    startup_handler: Option<Arc<FunctionInfo>>,
    shutdown_handler: Option<Arc<FunctionInfo>>,
    message_handlers: Vec<MessageProcessor>,
    task_locals: Option<TaskLocals>,
}

impl Application {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            startup_handler: None,
            shutdown_handler: None,
            message_handlers: Vec::new(),
            task_locals: None,
        }
    }

    pub async fn start(&mut self) {
        println!("Starting application: {}", self.name);
        let mut task_locals_copy = self.task_locals.clone().unwrap();
        let startup_handler = self.startup_handler.clone();
        let message_handlers = self.message_handlers.clone();
        match execute_event_handler(startup_handler, &task_locals_copy)
            .await {
            Ok(_) => (
                info!("Server starting..."),
            ),
            Err(e) => (
                println!("error {}", e),
            )
        };


        let (tx, mut rx) = tokio::sync::mpsc::channel(32);
        let mut msg_porter = Transporter::new(tx.clone(), self.name.clone());
        let tx = msg_porter.get_tx();

        let message_processors = self.message_handlers.clone();
        tokio::spawn(async move {
            let mh = message_handlers.clone();
            while let Some(message) = rx.recv().await {
                // println!("Received message: {:?}", message.clone());

                let input = Python::with_gil(|py| {
                    message.clone().into_py(py)
                });

                for mp in message_processors.iter() {
                    match execute_process_function(input.clone(), &mp.function, &task_locals_copy).await {
                        Ok(_) => (
                            info!("Server starting..."),
                        ),
                        Err(e) => (
                            println!("error {}", e),
                        )
                    };
                }
            }
        });

        match msg_porter.message_processor().await {
            Ok(_) => {
                info!("Message Porter started");
            }
            Err(e) => {
                println!("Message Porter error {}", e);
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

    pub fn add_message_handler(&mut self, mp: MessageProcessor) {
        self.message_handlers.push(mp);
    }
}