"use client";

import { useState, useRef } from "react";
import { AiOutlineUpload } from "react-icons/ai";
import { FaSpinner } from "react-icons/fa";
import { useRouter } from "next/navigation";

export default function Home() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  const fileInputRef = useRef(null);
  const router = useRouter();

  const alertMessages = [
    "broo first files upload maaduu 😂",
    "Egaaa Thanee heledheni File upload maaddu anthaa 🤣🤣",
    "Inu Last One chance broo focus maduu try to upload 🙃🙃",
  ];

  // ✅ FILE HANDLER (FILTER FOLDERS)
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);

    const onlyFiles = selectedFiles.filter(
      (file) => file.type !== "" && file.size > 0,
    );

    if (onlyFiles.length !== selectedFiles.length) {
      alert("Please select files only, not folders 📁❌");
    }

    setFiles(onlyFiles);
    setSuccess(false);
  };

  const handleUpload = async () => {
    if (!files.length) {
      if (alertCount >= 3) {
        router.push("/surprise");
        return;
      }

      const msg =
        alertCount < alertMessages.length
          ? alertMessages[alertCount]
          : alertMessages[Math.floor(Math.random() * alertMessages.length)];

      alert(msg);
      setAlertCount(alertCount + 1);
      return;
    }

    setLoading(true);
    setSuccess(false);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/upload_multiple_pos`,
        {
          method: "POST",
          body: formData,
        },
      );

      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "SAP_PO_Export.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);

      // ✅ RESET EVERYTHING
      setFiles([]);
      setSuccess(true);
      setAlertCount(0);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-b from-blue-100 to-blue-200">
      {/* Header */}
      <header className="bg-white shadow-md py-4">
        <div className="max-w-6xl mx-auto px-6 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-blue-600">SmartSAP</h1>
          <p className="text-gray-500">Effortless SAP PO Uploads</p>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-col items-center justify-center flex-1 py-16 px-6 text-center">
        <h2 className="text-4xl font-bold text-gray-700 mb-4">
          Upload Multiple Purchase Orders Instantly
        </h2>

        <p className="text-gray-600 mb-10 max-w-2xl">
          Drag & drop your PO files or select them manually. SmartSAP will
          convert them into SAP-ready Excel sheets in seconds.
        </p>

        {/* Upload Card */}
        <div className="bg-white shadow-xl rounded-2xl p-8 w-full max-w-lg">
          {/* ✅ LABEL BASED INPUT (BEST UX) */}
          <label className="border-2 border-dashed border-blue-300 rounded-xl p-6 text-center cursor-pointer hover:border-blue-500 transition block">
            <AiOutlineUpload className="mx-auto text-5xl text-blue-400 mb-4" />
            <p className="text-gray-500">
              Drag & drop files here or click to select
            </p>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          {/* File List */}
          {files.length > 0 && !success && (
            <ul className="mt-4 text-gray-700 text-left max-h-40 overflow-y-auto">
              {files.map((file, idx) => (
                <li
                  key={idx}
                  className="py-1 px-2 bg-blue-50 rounded mb-1 truncate"
                >
                  {file.name}
                </li>
              ))}
            </ul>
          )}

          {/* Success Message */}
          {success && (
            <div className="mt-4 py-2 px-4 bg-green-100 rounded text-green-700 font-semibold">
              ✅ File downloaded successfully! Check your downloads.
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={loading}
            className="mt-6 w-full cursor-pointer bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-3 transition"
          >
            {loading ? (
              <>
                <FaSpinner className="animate-spin" />
                Uploading...
              </>
            ) : (
              "Upload Files"
            )}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white shadow-inner py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-6 text-center text-gray-500">
          Made with <span className="text-red-500">❤️</span> by SmartSAP
        </div>
      </footer>
    </div>
  );
}
