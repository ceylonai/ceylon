use std::cell::RefCell;
use std::sync::{Arc, Mutex};
use pyo3::prelude::*;
use chrono::{DateTime, Utc};
use pyo3::types::{PyDict, PyString, PyTuple};

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

/// A function decorator that keeps track how often it is called.
///
/// It otherwise doesn't do anything special.
#[pyclass(name = "MessageProcessor")]
pub struct MessageProcessor {
    // This is the actual function being wrapped.
    pub(crate) wraps: Arc<Mutex<Py<PyAny>>>,
}

#[pymethods]
impl MessageProcessor {
    // Note that we don't validate whether `wraps` is actually callable.
    //
    // While we could use `PyAny::is_callable` for that, it has some flaws:
    //    1. It doesn't guarantee the object can actually be called successfully
    //    2. We still need to handle any exceptions that the function might raise
    #[new]
    fn __new__(wraps: Py<PyAny>) -> Self {
        MessageProcessor {
            wraps: Arc::new(Mutex::new(wraps)),
        }
    }

    fn start<'a>(&'a self, py: Python<'a>) -> PyResult<&'a PyAny> {
        let func = self.wraps.lock().unwrap().clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            Python::with_gil(|py| {
                let func = func.into_ref(py);
                let name = func.getattr("__name__").unwrap();
                println!("Function name: {}", name.to_string());
                let msg = format!("Function name: {}", name.to_string());
                let msg = PyString::new(py, &msg);
                let args = PyTuple::new(py, &[msg]);
                let kwargs = PyDict::new(py);
                let ret = func.call(args, Option::from(kwargs))?;

                Ok(())
            })
        })
    }
}


/// A Python module implemented in Rust.
#[pymodule]
fn rakun(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_time, m)?)?;
    m.add_class::<MessageProcessor>()?;
    Ok(())
}