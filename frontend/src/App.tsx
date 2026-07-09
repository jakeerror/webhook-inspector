import { Route, Routes } from "react-router-dom";

import { BinPage } from "./pages/BinPage";
import { HomePage } from "./pages/HomePage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/b/:id" element={<BinPage />} />
    </Routes>
  );
}
