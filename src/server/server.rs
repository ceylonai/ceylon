use std::sync::Arc;

use log::{debug, error, info};
use pyo3::{PyAny, pyclass, pymethods, PyResult, Python};
use tokio::sync::Mutex;

use crate::server::application;
use crate::transport::p2p::P2PTransporter;
use crate::transport::redis::RedisTransporter;
use crate::types::{EventProcessor, FunctionInfo};

// pyO3 module

#[pyclass]
pub struct MessageProcessor {
    pub msg_tx: Arc<Mutex<tokio::sync::mpsc::Sender<String>>>,
}

#[pymethods]
impl MessageProcessor {
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
    app_rx: Arc<Mutex<tokio::sync::mpsc::Receiver<String>>>,
    app_tx: tokio::sync::mpsc::Sender<String>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        let (msg_tx, msg_rx) = tokio::sync::watch::channel::<String>("".to_string());
        let (app_tx, app_rx) = tokio::sync::mpsc::channel::<String>(100);
        Self {
            application: Arc::new(std::sync::Mutex::new(application::Application::new(name, msg_rx))),
            msg_tx: Arc::new(std::sync::Mutex::new(msg_tx)),
            app_rx: Arc::new(Mutex::new(app_rx)),
            app_tx,
        }
    }
    pub fn start(&mut self, py: Python) -> PyResult<()> {
        let application = self.application.clone();
        let asyncio = py.import("asyncio")?;
        let event_loop = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (event_loop, ))?;

        let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;

        let msg_tx = self.msg_tx.clone();
        let app_rx = self.app_rx.clone();
        std::thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                while let msg = app_rx.lock().await.recv().await.unwrap() {
                    debug!(
                        "[MessageProcessor] Sent Dispatch Message to [Server]-1: {}",
                        msg.clone()
                    );
                    match msg_tx.lock() {
                        Ok(mstx) => {
                            match mstx.send(msg.clone())
                            {
                                Ok(_) => {
                                    debug!("Sent message-1");
                                }
                                Err(e) => {
                                    error!("error {}", e);
                                }
                            }
                        }
                        Err(e) => {
                            error!("error {}", e);
                        }
                    };
                }
            })
        });

        std::thread::spawn(move || {
            let mut application = application.lock().unwrap();
            application.initialize(task_locals.clone());

            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(async move {
                    let boot = application.boot();
                    let shutdown = application.shutdown();
                    let t1 = tokio::spawn(async move {
                        match boot {
                            Some(mut a) => {
                                a.execute().await;
                            }
                            None => {
                                debug!("Boot completed");
                            }
                        };
                    });

                    application.start::<P2PTransporter>().await;


                    let t2 = tokio::spawn(async move {
                        match shutdown {
                            Some(mut a) => {
                                a.execute().await;
                            }
                            None => {
                                debug!("Shutdown completed");
                            }
                        };
                    });

                    tokio::select! {
                        _ = t1 => {
                            debug!("Boot completed");
                        },
                        _ = t2 => {
                            debug!("Shutdown completed");
                        },
                    }
                })
        });

        let event_loop = (*event_loop).call_method0("run_forever");
        if event_loop.is_err() {
            println!("Ctrl c handler");
            error!("{}", event_loop.err().unwrap());

            let mut application = self.application.lock().unwrap();
            application.shutdown();
            std::process::abort();
        }

        Ok(())
    }

    pub fn publisher(&mut self) -> MessageProcessor {
        MessageProcessor {
            msg_tx: Arc::new(Mutex::new(self.app_tx.clone())),
        }
    }

    pub fn add_startup_handler(&mut self, mp: EventProcessor) {
        let mut application = self.application.lock().unwrap();
        application.add_startup_handler(mp.function);
    }
    pub fn add_shutdown_handler(&mut self, mp: EventProcessor) {
        let mut application = self.application.lock().unwrap();
        application.add_shutdown_handler(mp.function);
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
