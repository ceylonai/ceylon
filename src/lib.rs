use std::cell::RefCell;
use pyo3::prelude::*;
use chrono::{DateTime, Utc};

thread_local! {
    static START_TIME: RefCell<DateTime<Utc>> = RefCell::new(Utc::now());
}


/// Formats the sum of two numbers as string.
#[pyfunction]
fn get_time() -> PyResult<String> {
    let start_time = START_TIME.with(|start_time| *start_time.borrow());
    println!(" Start time: {}", start_time.format("%Y-%m-%d %H:%M:%S.%f").to_string());
    Ok(start_time.format("%Y-%m-%d %H:%M:%S.%f").to_string())
}


/// A Python module implemented in Rust.
#[pymodule]
fn rakun(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_time, m)?)?;
    Ok(())
}