use async_trait::async_trait;
use libp2p::futures::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};
use libp2p::request_response::Codec;
use serde_json;
use std::{fmt, io};
use crate::protocol::anp::AnpMessage;

#[derive(Debug, Clone)]
pub struct AnpRequest(pub AnpMessage);

impl fmt::Display for AnpRequest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let AnpRequest(msg) = self;
        write!(f, "AnpRequest(from: {}, to: {}, type: {})", 
               msg.from, msg.to, msg.msg_type)
    }
}

#[derive(Debug, Clone)]
pub struct AnpResponse(pub AnpMessage);

impl fmt::Display for AnpResponse {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let AnpResponse(msg) = self;
        write!(f, "AnpResponse(from: {}, to: {}, type: {})", 
               msg.from, msg.to, msg.msg_type)
    }
}

#[derive(Clone, Default)]
pub struct AnpCodec();

#[async_trait]
impl Codec for AnpCodec {
    type Protocol = &'static str;
    type Request = AnpRequest;
    type Response = AnpResponse;

    async fn read_request<T>(&mut self, _: &Self::Protocol, io: &mut T) -> io::Result<Self::Request>
    where
        T: AsyncRead + Unpin + Send,
    {
        let mut buf = Vec::new();
        io.read_to_end(&mut buf).await?;

        if buf.is_empty() {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                "No data to read",
            ));
        }

        let msg = serde_json::from_slice::<AnpMessage>(&buf)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        Ok(AnpRequest(msg))
    }

    async fn read_response<T>(
        &mut self,
        _: &Self::Protocol,
        io: &mut T,
    ) -> io::Result<Self::Response>
    where
        T: AsyncRead + Unpin + Send,
    {
        let mut buf = Vec::new();
        io.read_to_end(&mut buf).await?;

        if buf.is_empty() {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                "No data to read",
            ));
        }

        let msg = serde_json::from_slice::<AnpMessage>(&buf)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        Ok(AnpResponse(msg))
    }

    async fn write_request<T>(
        &mut self,
        _: &Self::Protocol,
        io: &mut T,
        req: Self::Request,
    ) -> io::Result<()>
    where
        T: AsyncWrite + Unpin + Send,
    {
        let AnpRequest(msg) = req;
        let data =
            serde_json::to_vec(&msg).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        io.write_all(&data).await?;
        Ok(())
    }

    async fn write_response<T>(
        &mut self,
        _: &Self::Protocol,
        io: &mut T,
        res: Self::Response,
    ) -> io::Result<()>
    where
        T: AsyncWrite + Unpin + Send,
    {
        let AnpResponse(msg) = res;
        let data =
            serde_json::to_vec(&msg).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        io.write_all(&data).await?;
        Ok(())
    }
}

// Protocol identifier constant
pub const ANP_PROTOCOL: &str = "/anp/1.0.0";
