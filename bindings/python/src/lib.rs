mod agent;

use pyo3::prelude::*;


#[pyfunction]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").into()
}

/// A Python module implemented in Rust.
#[pymodule]
fn ceylonai(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_version, m)?)?;


    m.add_class::<agent::agent::AbstractAgent>()?;


    Ok(())
}
