import { Route, Routes } from "react-router-dom";
import InputPage from "./pages/InputPage";
import LandingPage from "./pages/LandingPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/start" element={<InputPage />} />
      <Route path="/result" element={<ResultPage />} />
    </Routes>
  );
}
