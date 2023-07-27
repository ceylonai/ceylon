use std::sync::Arc;

use lazy_static::lazy_static;
use log::{debug, info};
use pyo3::{PyAny, pyclass, pymethods, PyResult, Python};
use tokio::sync::Mutex;

use crate::server::application;
use crate::transport::p2p::P2PTransporter;
use crate::types::EventProcessor;

// pyO3 module

lazy_static! {
    pub static ref RX_TX: Arc<
        std::sync::Mutex<(
            tokio::sync::mpsc::Sender<String>,
            tokio::sync::mpsc::Receiver<String>
        )>,
    > = Arc::new( std::sync::Mutex::new(tokio::sync::mpsc::channel::<String>(100)));
}

#[pyclass]
pub struct MessageProcessor {
    pub msg_tx: Arc<Mutex<tokio::sync::mpsc::Sender<String>>>,
    pub msg_rx: Arc<Mutex<tokio::sync::mpsc::Receiver<String>>>,
}

#[pymethods]
impl MessageProcessor {
    #[new]
    fn new() -> Self {
        let (msg_tx, msg_rx) = tokio::sync::mpsc::channel::<String>(100);
        Self {
            msg_tx: Arc::new(Mutex::new(msg_tx)),
            msg_rx: Arc::new(Mutex::new(msg_rx)),
        }
    }

    fn start(&mut self) {
        let app_rx = self.msg_rx.clone();
        let app_tx = RX_TX.lock().unwrap().0.clone();
        std::thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                let mut app_rx = app_rx.lock().await;
                while let msg = app_rx.recv().await.unwrap() {
                    app_tx.send(msg).await.unwrap();
                }
            })
        });
    }

    pub fn publish<'a>(&'a mut self, py: Python<'a>, message: String) -> PyResult<&'a PyAny> {
        info!(
            "[Agent] Sent Dispatch Message to [MessageProcessor]-0: {}",
            message
        );

        let msg_server_rx = self.msg_tx.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            msg_server_rx.lock().await.send(message.clone()).await.unwrap();
            Ok(Python::with_gil(|py| py.None()))
        })
    }
}

#[pyclass]
pub struct Server {
    application: Arc<std::sync::Mutex<application::Application>>,
    msg_tx: Arc<std::sync::Mutex<tokio::sync::watch::Sender<String>>>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        let (msg_tx, msg_rx) = tokio::sync::watch::channel::<String>("".to_string());
        Self {
            application: Arc::new(std::sync::Mutex::new(application::Application::new(name, msg_rx))),
            msg_tx: Arc::new(std::sync::Mutex::new(msg_tx)),
        }
    }
    pub fn start(&mut self, py: Python) -> PyResult<()> {
        let application = self.application.clone();
        let asyncio = py.import("asyncio")?;
        let event_loop = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (event_loop, ))?;

        let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;

        let msg_tx = self.msg_tx.clone();
        std::thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                while let msg = RX_TX.lock().unwrap().1.recv().await.unwrap() {
                    debug!(
                        "[MessageProcessor] Sent Dispatch Message to [Server]-1: {}",
                        msg.clone()
                    );
                    msg_tx.lock().unwrap().send(msg).unwrap();
                }
            })
        });

        std::thread::spawn(move || {
            let mut application = application.lock().unwrap();
            application.initialize(task_locals.clone());

            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(async move {
                    application.start::<P2PTransporter>().await;
                })
        });

        let event_loop = (*event_loop).call_method0("run_forever");
        if event_loop.is_err() {
            println!("Ctrl c handler");
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

    pub fn remove_message_handler(&mut self, mp: EventProcessor) {
        let mut application = self.application.lock().unwrap();
        application.remove_message_handler(mp);
    }
}
