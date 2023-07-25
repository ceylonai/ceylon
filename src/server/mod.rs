use std::sync::{Arc, Mutex};

use log::{debug, info};
use pyo3::{pyclass, pymethods};
// pyO3 module
use pyo3::prelude::*;

use crate::types::{FunctionInfo, MessageProcessor};

mod application;

#[pyclass]
pub struct Server {
    application: Arc<Mutex<application::Application>>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        Self {
            application: Arc::new(Mutex::new(application::Application::new(name))),
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
            // Python::with_gil(|py| {
            //     pyo3_asyncio::tokio::run(py, async move {
            //         execute_event_handler(shutdown_handler, &task_locals.clone())
            //             .await
            //             .unwrap();
            //         Ok(())
            //     })
            // })?;
            std::process::abort();
        }

        Ok(())
    }

    // pub fn start(
    //     &mut self,
    //     py: Python,
    //     workers: usize,
    // ) -> PyResult<()> {
    //     let asyncio = py.import("asyncio")?;
    //     let event_loop = asyncio.call_method0("new_event_loop")?;
    //     asyncio.call_method1("set_event_loop", (event_loop, ))?;
    //
    //     let startup_handler = self.startup_handler.clone();
    //     let shutdown_handler = self.shutdown_handler.clone();
    //     let message_handlers = self.message_handlers.clone();
    //
    //     let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;
    //     let task_locals_copy = task_locals.clone();
    //     let task_locals_copy2 = task_locals.clone();
    //
    //
    //     let (msg_tx, mut rx) = tokio::sync::mpsc::channel::<DataMessage>(32);
    //     // let tx2 = tx.clone();
    //
    //
    //     std::thread::spawn(move || {
    //         tokio::runtime::Runtime::new().unwrap().block_on(async move {
    //             println!("Starting server 111");
    //             match execute_event_handler(startup_handler.clone(), &task_locals_copy)
    //                 .await {
    //                 Ok(_) => (
    //                     println!("Starting server"),
    //                 ),
    //                 Err(e) => (
    //                     println!("error {}", e),
    //                 )
    //             }
    //         });
    //
    //         println!("Starting server");
    //
    //         tokio::runtime::Runtime::new().unwrap().block_on(async move {
    //             while let Some(message) = rx.recv().await {
    //                 println!("Received message: {:?}", message.clone());
    //                 let input = Python::with_gil(|py| {
    //                     message.clone().into_py(py)
    //                 });
    //                 let mh = message_handlers.lock().unwrap();
    //                 for mp in mh.iter() {
    //                     execute_process_function(input.clone(), &mp.function, &task_locals_copy2)
    //                         .await
    //                         .unwrap();
    //                 }
    //             }
    //         });
    //     });
    //
    //     let name = self.name.clone();
    //     let server_name = name.to_string();
    //
    //     tokio::runtime::Runtime::new().unwrap().block_on(async move {
    //         let (tx, mut rx) = tokio::sync::mpsc::channel(32);
    //         let mut msg_porter = Transporter::new(tx.clone(), server_name);
    //         let tx = msg_porter.get_tx();
    //
    //
    //         tokio::spawn(async move {
    //             loop {
    //                 let msg = tokio::select! {
    //                     Some(msg) = rx.recv() => msg,
    //                 };
    //                 match msg_tx.send(msg).await {
    //                     Ok(_) => {
    //                         info!("Sent message");
    //                     }
    //                     Err(e) => {
    //                         println!("error {}", e);
    //                     }
    //                 };
    //             }
    //         });
    //
    //
    //         tokio::spawn(async move {
    //             for i in 0..1000 {
    //                 match tx.send(format!("Hi {}", i)).await {
    //                     Ok(_) => {
    //                         info!("Sent message {}", i);
    //                     }
    //                     Err(e) => {
    //                         error!("error {}", e);
    //                     }
    //                 };
    //                 // sleep
    //                 tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    //             }
    //         });
    //         msg_porter.message_processor().await.expect("TODO: panic message");
    //     });
    //
    //
    //     let event_loop = (*event_loop).call_method0("run_forever");
    //     if event_loop.is_err() {
    //         debug!("Ctrl c handler");
    //         info!("{}", event_loop.err().unwrap());
    //         Python::with_gil(|py| {
    //             pyo3_asyncio::tokio::run(py, async move {
    //                 execute_event_handler(shutdown_handler, &task_locals.clone())
    //                     .await
    //                     .unwrap();
    //                 Ok(())
    //             })
    //         })?;
    //         std::process::abort();
    //     }
    //     Ok(())
    // }
    //
    pub fn add_message_handler(&mut self, mp: MessageProcessor) {
        // debug!("Added message handler {:?}", self.message_handlers.len());
        let mut application = self.application.lock().unwrap();
        application.add_message_handler(mp);
    }

    pub fn remove_message_handler(&mut self, function: FunctionInfo) {
        // Remove the message handler
    }

    /// Add a new startup handler
    pub fn add_startup_handler(&mut self, function: FunctionInfo) {
        let mut application = self.application.lock().unwrap();
        application.set_startup_handler(function);
    }

    /// Add a new shutdown handler
    pub fn add_shutdown_handler(&mut self, function: FunctionInfo) {
        let mut application = self.application.lock().unwrap();
        application.set_shutdown_handler(function);
    }
}