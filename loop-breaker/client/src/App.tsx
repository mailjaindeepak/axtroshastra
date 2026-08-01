import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Episodes from "./pages/Episodes";
import LogToday from "./pages/LogToday";
import Sql from "./pages/trackers/Sql";
import AiMl from "./pages/trackers/AiMl";
import Dsa from "./pages/trackers/Dsa";
import Gym from "./pages/trackers/Gym";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/episodes" element={<Episodes />} />
        <Route path="/log" element={<LogToday />} />
        <Route path="/sql" element={<Sql />} />
        <Route path="/ai-ml" element={<AiMl />} />
        <Route path="/dsa" element={<Dsa />} />
        <Route path="/gym" element={<Gym />} />
      </Routes>
    </BrowserRouter>
  );
}
