use std::cell::RefCell;

use chrono::{DateTime, Utc};
use pyo3::prelude::*;

mod server;
mod types;
mod executor;
mod transport;

thread_local! {
    static START_TIME: RefCell<DateTime<Utc>> = RefCell::new(Utc::now());
}


/// Formats the sum of two numbers as string.
#[pyfunction]
fn get_start_time() -> PyResult<String> {
    let start_time = START_TIME.with(|start_time| *start_time.borrow());
    println!(" Start time: {}", start_time.format("%Y-%m-%d %H:%M:%S.%f").to_string());
    Ok(start_time.format("%Y-%m-%d %H:%M:%S.%f").to_string())
}

#[pyfunction]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").into()
}

/// A Python module implemented in Rust.
#[pymodule]
fn rakun(_py: Python, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(get_start_time, m)?)?;
    // Classes
    m.add_class::<types::FunctionInfo>()?;
    m.add_class::<types::MessageProcessor>()?;
    m.add_class::<types::DataMessage>()?;
    m.add_class::<types::DataMessagePublisher>()?;
    m.add_class::<server::Server>()?;
    pyo3::prepare_freethreaded_python();
    Ok(())
}