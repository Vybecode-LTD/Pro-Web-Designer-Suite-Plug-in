import styled from "styled-components";

export const Backdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
`;

export const Dialog = styled.div`
  padding: 24px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.07), 0 24px 48px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  transition: opacity 250ms ease-out;
`;

export const Title = styled.h2`
  font-size: 22px;
  margin: 0 0 12px;
  color: #111;
`;
