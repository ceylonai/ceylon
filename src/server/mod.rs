use std::sync::Arc;

use log::{debug, info};
use pyo3::{pyclass, pymethods};
// pyO3 module
use pyo3::prelude::*;

use crate::executor::execute_event_handler;
use crate::types::FunctionInfo;

#[pyclass]
pub struct Server {
    name: Arc<String>,
    startup_handler: Option<Arc<FunctionInfo>>,
    shutdown_handler: Option<Arc<FunctionInfo>>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new(name: &str) -> Self {
        Self {
            name: Arc::new(name.to_string()),
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

        let task_locals = pyo3_asyncio::TaskLocals::new(event_loop).copy_context(py)?;
        let task_locals_copy = task_locals.clone();

        std::thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async move {
                debug!("Starting server {}",name);
                execute_event_handler(startup_handler, &task_locals_copy)
                    .await
                    .unwrap();

                loop {
                    tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
                }
            });
        });

        let task_locals_copy = task_locals.clone();
        // let event_loop = (*event_loop).call_method0("run_forever");
        // if event_loop.is_err() {
        //     debug!("Ctrl c handler");
        //     Python::with_gil(|py| {
        //         pyo3_asyncio::tokio::run(py, async move {
        //             execute_event_handler(shutdown_handler, &task_locals_copy)
        //                 .await
        //                 .unwrap();
        //             Ok(())
        //         })
        //     })?;
        //     std::process::abort();
        // }

        Ok(())
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