import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import TopicList from "./components/TopicList";
import TopicDetail from "./components/TopicDetail";
import LabelList from "./components/LabelList";
import LabelDetail from "./components/LabelDetail";
import MethodologyPage from "./components/MethodologyPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TopicList />} />
        <Route path="/topic/:id" element={<TopicDetail />} />
        <Route path="/labels" element={<LabelList />} />
        <Route path="/labels/:id" element={<LabelDetail />} />
        <Route path="/methodology" element={<MethodologyPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
