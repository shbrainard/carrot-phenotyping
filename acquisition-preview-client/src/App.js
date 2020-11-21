import React, { useState, useEffect, useRef } from "react";

import { Message } from "semantic-ui-react";
import styled from "styled-components";

const Wrapper = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
`;

const StatusWrapper = styled.div`
  position: absolute;
  top: 0;
  right: 15px;
  width: 200px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  z-index: 5;
`;

const ImageWrapper = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
`;

const Img = styled.img`
  display: ${props => (props.hidden ? "hidden" : "block")};
  height: 100%;
  width: 100%;
  object-fit: contain;
`;

function App() {
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [overlay, setOverlay] = useState(null);
  const [mask, setMask] = useState(null);

  const maskImage = useRef();
  const overlayImage = useRef();

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:7777`);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = ({ data }) => {
      setLoading(true);
      const response = JSON.parse(data);

      if (response.responseData.type === "overlay") {
        overlayImage.current.src = `data:image/jpeg;base64,${
          response.responseData.src
        }`;
        setOverlay(true);
      }
      if (response.responseData.type === "mask") {
        maskImage.current.src = `data:image/jpeg;base64,${
          response.responseData.src
        }`;
      }
      setMask(true);
      setLoading(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <Wrapper>
      <StatusWrapper>
        {!connected && !loading && (
          <Message color="yellow">Connecting to server...</Message>
        )}
        {connected && !loading && <Message color="green">Connected!</Message>}
        {loading && <Message color="yellow">Loading...</Message>}
      </StatusWrapper>
      <ImageWrapper>
        {mask === null && <p>Waiting for image...</p>}
        {<Img ref={maskImage} hidden={mask === null} />}
      </ImageWrapper>
      <ImageWrapper>
        {overlay === null && <p>Waiting for image...</p>}
        {<Img ref={overlayImage} hidden={overlay === null} />}
      </ImageWrapper>
    </Wrapper>
  );
}

export default App;
