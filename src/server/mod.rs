use std::sync::{Arc, Mutex};

use log::{debug, error, info};
use pyo3::{pyclass, pymethods};
// pyO3 module
use pyo3::prelude::*;

use crate::executor::{execute_event_handler, execute_process_function};
use crate::transport::{Transporter};
use crate::types::{FunctionInfo, MessageProcessor};

#[pyclass]
pub struct Server {
    name: Arc<String>,
    startup_handler: Option<Arc<FunctionInfo>>,
    shutdown_handler: Option<Arc<FunctionInfo>>,
    message_handlers: Arc<Mutex<Vec<MessageProcessor>>>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        Self {
            name: Arc::new(name.to_string()),
            message_handlers: Arc::new(Mutex::new(Vec::new())),
            startup_handler: None,
            shutdown_handler: None,
        }
    }

    pub fn start(
        &mut self,
        py: Python,
        workers: usize,
    ) -> PyResult<()> {
        let name = self.name.clone();

        let asyncio = py.import("asyncio")?;
        let event_loop = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (event_loop, ))?;

        let startup_handler = self.startup_handler.clone();
        let shutdown_handler = self.shutdown_handler.clone();
        let message_handlers = self.message_handlers.clone();

        let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;
        let task_locals_copy = task_locals.clone();
        let task_locals_copy2 = task_locals.clone();


        let (tx, mut rx) = tokio::sync::mpsc::channel(32);
        let tx2 = tx.clone();


        std::thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                execute_event_handler(startup_handler.clone(), &task_locals_copy)
                    .await
                    .unwrap();
            });


            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                debug!("Listening server {}",name);
                while let Some(message) = rx.recv().await {
                    debug!("Received message {}",message);
                    let mh = message_handlers.lock().unwrap();
                    for mp in mh.iter() {
                        execute_process_function(message, &mp.function, &task_locals_copy2)
                            .await
                            .unwrap();
                    }
                }
            });
        });


        tokio::runtime::Runtime::new().unwrap().block_on(async move {
            let (tx, mut rx) = tokio::sync::mpsc::channel(32);
            let mut msg_porter = Transporter::new(tx.clone());
            let tx = msg_porter.get_tx();


            tokio::spawn(async move {
                loop {
                    println!("Test loop");
                    let msg = tokio::select! {
                        Some(msg) = rx.recv() => msg,
                    };
                    println!("Got {:?}", msg);
                }
            });


            tokio::spawn(async move {
                for i in 0..1000 {
                    match tx.send(format!("Hi {}", i)).await {
                        Ok(_) => {
                            info!("Sent message {}", i);
                        }
                        Err(e) => {
                            error!("error {}", e);
                        }
                    };
                    // sleep
                    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                }
            });
            msg_porter.message_processor().await.expect("TODO: panic message");
        });


        let event_loop = (*event_loop).call_method0("run_forever");
        if event_loop.is_err() {
            debug!("Ctrl c handler");
            info!("{}", event_loop.err().unwrap());
            Python::with_gil(|py| {
                pyo3_asyncio::tokio::run(py, async move {
                    execute_event_handler(shutdown_handler, &task_locals.clone())
                        .await
                        .unwrap();
                    Ok(())
                })
            })?;
            std::process::abort();
        }
        Ok(())
    }

    pub fn add_message_handler(&mut self, mp: MessageProcessor) {
        // debug!("Added message handler {:?}", self.message_handlers.len());
        let mut handlers = self.message_handlers.lock().unwrap();
        // Push the new handler to the Vec
        handlers.push(mp);
    }

    pub fn remove_message_handler(&mut self, function: FunctionInfo) {
        // Remove the message handler
    }

    /// Add a new startup handler
    pub fn add_startup_handler(&mut self, function: FunctionInfo) {
        self.startup_handler = Some(Arc::new(function));
        info!("Added startup handler {:?}", self.startup_handler);
    }

    /// Add a new shutdown handler
    pub fn add_shutdown_handler(&mut self, function: FunctionInfo) {
        self.shutdown_handler = Some(Arc::new(function));
        info!("Added shutdown handler {:?}", self.shutdown_handler);
    }
}