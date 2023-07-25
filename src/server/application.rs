use std::sync::{Arc, Mutex};

use pyo3_asyncio::TaskLocals;

use crate::executor::execute_event_handler;
use crate::types::{FunctionInfo, MessageProcessor};

pub(crate) struct Application {
    name: String,
    startup_handler: Option<Arc<FunctionInfo>>,
    shutdown_handler: Option<Arc<FunctionInfo>>,
    message_handlers: Arc<Mutex<Vec<MessageProcessor>>>,
    task_locals: Option<TaskLocals>,
}

impl Application {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            startup_handler: None,
            shutdown_handler: None,
            message_handlers: Arc::new(Mutex::new(Vec::new())),
            task_locals: None,
        }
    }

    pub async fn start(&mut self) {
        println!("Starting application: {}", self.name);

        let mut task_locals_copy = self.task_locals.clone().unwrap();
        let startup_handler = self.startup_handler.clone();
        match execute_event_handler(startup_handler, &task_locals_copy)
            .await {
            Ok(_) => (
                println!("Starting server"),
            ),
            Err(e) => (
                println!("error {}", e),
            )
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
        let mut message_handlers = self.message_handlers.lock().unwrap();
        message_handlers.push(mp);
    }
}