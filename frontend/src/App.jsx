import { Link, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import BatchPage from "./pages/BatchPage";
import HistoryPage from "./pages/HistoryPage";
import SubmitPage from "./pages/SubmitPage";

function NotFound() {
  return (
    <div className="py-20 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/" className="mt-4 inline-block text-indigo-600 hover:underline dark:text-indigo-400">
        Back to home
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SubmitPage />} />
        <Route path="dashboard" element={<HistoryPage />} />
        <Route path="batch" element={<BatchPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
