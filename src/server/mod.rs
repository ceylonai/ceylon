use std::sync::{Arc, Mutex};
use lazy_static::lazy_static;

use log::{debug, info};
use pyo3::{pyclass, pymethods};
// pyO3 module
use pyo3::prelude::*;
use crate::transport::p2p::P2PTransporter;
use crate::transport::Transporter;

use crate::types::{EventProcessor, FunctionInfo};

mod application;

lazy_static! {
    pub static ref RX_TX: Arc<Mutex<(std::sync::mpsc::Sender<String>,std::sync::mpsc::Receiver<String>)>>
    = Arc::new(Mutex::new(std::sync::mpsc::channel::<String>()));
}

#[pyclass]
pub struct MessageProcessor {
    pub msg_tx: std::sync::mpsc::Sender<String>,
    pub msg_rx: Arc<Mutex<std::sync::mpsc::Receiver<String>>>,
}

#[pymethods]
impl MessageProcessor {
    #[new]
    fn new() -> Self {
        let (msg_tx, msg_rx) = std::sync::mpsc::channel::<String>();
        Self {
            msg_tx,
            msg_rx: Arc::new(Mutex::new(msg_rx)),
        }
    }

    fn start(&mut self) {
        let mut app_rx = self.msg_rx.clone();
        let mut app_tx = RX_TX.lock().unwrap().0.clone();
        std::thread::spawn(move || {
            while let Ok(msg) = app_rx.lock().unwrap().recv() {
                app_tx.send(msg).unwrap();
            }
        });
    }

    fn publish(&mut self, message: String) {
        debug!("[Agent] Sent Dispatch Message to [MessageProcessor]-0: {}", message);

        //
        match self.msg_tx.send(message) {
            Ok(_) => {
                debug!("Sent message");
            }
            Err(e) => {
                debug!("error 33 {}", e);
            }
        };
    }
}


#[pyclass]
pub struct Server {
    application: Arc<Mutex<application::Application>>,
    msg_tx: Arc<Mutex<tokio::sync::watch::Sender<String>>>,
    msg_processor: Option<MessageProcessor>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        let (msg_tx, msg_rx) = tokio::sync::watch::channel::<String>("".to_string());
        Self {
            application: Arc::new(Mutex::new(application::Application::new(name, msg_rx))),
            msg_tx: Arc::new(Mutex::new(msg_tx)),
            msg_processor: None,
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

        let msg_tx = self.msg_tx.clone();
        std::thread::spawn(move || {
            while let Ok(msg) = RX_TX.lock().unwrap().1.recv() {
                debug!("[MessageProcessor] Sent Dispatch Message to [Server]-1: {}", msg.clone());
                msg_tx.lock().unwrap().send(msg).unwrap();
            }
        });

        std::thread::spawn(move || {
            let mut application = application.lock().unwrap();
            application.initialize(task_locals.clone());

            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                application.start::<P2PTransporter>().await;
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

    pub fn add_event_processor(&mut self, mp: EventProcessor) {
        let mut application = self.application.lock().unwrap();
        application.add_event_processor(mp);
    }

    pub fn remove_message_handler(&mut self, function: FunctionInfo) {
        // Remove the message handler
    }
}