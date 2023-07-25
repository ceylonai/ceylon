use std::sync::{Arc, Mutex};

use log::{debug, info};
use pyo3::{pyclass, pymethods};
// pyO3 module
use pyo3::prelude::*;

use crate::types::{FunctionInfo, EventProcessor};

mod application;

#[pyclass]
pub struct Server {
    application: Arc<Mutex<application::Application>>,
    msg_tx: tokio::sync::watch::Sender<String>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        let (tx, msg_rx) = tokio::sync::watch::channel::<String>("".to_string());
        Self {
            application: Arc::new(Mutex::new(application::Application::new(name, msg_rx))),
            msg_tx: tx,
        }
    }

    pub fn start(
        &mut self,
        py: Python,
        workers: usize,
    ) -> PyResult<()> {
        let mut application = self.application.clone();
        let asyncio = py.import("asyncio")?;
        let event_loop = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (event_loop, ))?;

        let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;

        std::thread::spawn(move || {
            let mut application = application.lock().unwrap();
            application.initialize(task_locals.clone());


            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                application.start().await;
            })
        });


        let event_loop = (*event_loop).call_method0("run_forever");
        if event_loop.is_err() {
            debug!("Ctrl c handler");
            info!("{}", event_loop.err().unwrap());

            let mut application = self.application.lock().unwrap();
            application.shutdown();
            std::process::abort();
        }

        Ok(())
    }

    pub fn publish(
        &mut self,
        py: Python,
        message: &str,
    ) -> PyResult<()> {
        match self.msg_tx.send(message.to_string()) {
            Ok(_) => {
                info!("Sent message");
            }
            Err(e) => {
                println!("error {}", e);
            }
        };
        Ok(())
    }

    pub fn add_event_processor(&mut self, mp: EventProcessor) {
        let mut application = self.application.lock().unwrap();
        application.add_event_processor(mp);
    }

    pub fn remove_message_handler(&mut self, function: FunctionInfo) {
        // Remove the message handler
    }

    // /// Add a new startup handler
    // pub fn add_startup_handler(&mut self, function: FunctionInfo) {
    //     let mut application = self.application.lock().unwrap();
    //     application.set_startup_handler(function);
    // }
    //
    // /// Add a new shutdown handler
    // pub fn add_shutdown_handler(&mut self, function: FunctionInfo) {
    //     let mut application = self.application.lock().unwrap();
    //     application.set_shutdown_handler(function);
    // }
    // /// Add a new shutdown handler
    // pub fn add_background_processor(&mut self, function: FunctionInfo) {
    //     let mut application = self.application.lock().unwrap();
    //     application.set_background_processor(function);
    // }
}