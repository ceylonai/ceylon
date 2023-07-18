use pyo3::prelude::*;


#[pyclass]
struct Agent {
    name: String,
}

#[pymethods]
impl Agent {
    #[new]
    fn new(name: String) -> Self {
        Self { name }
    }

    fn get_name(&self) -> String {
        self.name.to_string()
    }
}


/// A Python module implemented in Rust.
#[pymodule]
fn rakun(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Agent>()?;
    Ok(())
}