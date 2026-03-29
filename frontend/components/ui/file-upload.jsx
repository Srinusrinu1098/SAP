import { cn } from "@/lib/utils";
import React, { useRef, useState } from "react";
import { motion } from "framer-motion";
import { IconUpload, IconX } from "@tabler/icons-react";
import { useDropzone } from "react-dropzone";
import { Loader2Icon } from "lucide-react";
import { Button } from "./button";
import Link from "next/link";

export const FileUpload = ({ onChange }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const fileInputRef = useRef(null);

  const handleFileChange = (newFiles) => {
    setLoading(true);
    setFiles(newFiles);
    onChange && onChange(newFiles);
  };

  const handleCancel = () => {
    setFiles([]);
    setLoading(false);
  };

  const { getRootProps, isDragActive } = useDropzone({
    multiple: false,
    noClick: true,
    onDrop: handleFileChange,
    onDropRejected: (error) => {
      console.log(error);
    },
  });

  return (
    <div className="border border-black rounded-2xl" {...getRootProps()}>
      <motion.div
        onClick={() => {
          if (!loading) fileInputRef.current?.click();
        }}
        whileHover="animate"
        className={cn(
          "p-10 rounded-2xl transition-all duration-300 border border-dashed bg-white dark:bg-neutral-900 hover:border-blue-400 w-full relative overflow-hidden",
          loading ? "pointer-events-none opacity-60" : "cursor-pointer"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={(e) => handleFileChange(Array.from(e.target.files || []))}
          disabled={files.length > 0}
          className="hidden"
        />

        <div className="absolute inset-0 z-0 [mask-image:radial-gradient(ellipse_at_center,white,transparent)]">
          <GridPattern />
        </div>

        <div className="flex flex-col items-center justify-center relative z-10">
          <p className="text-lg font-semibold text-neutral-700 dark:text-neutral-300">
            Upload Your Resume
          </p>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Drag & drop, or click to select a PDF
          </p>

          <div className="mt-10 w-full max-w-xl mx-auto">
            {files.length > 0 ? (
              files.map((file, idx) => (
                <motion.div
                  key={"file" + idx}
                  className="relative flex flex-col items-center justify-center bg-white dark:bg-neutral-800 p-5 rounded-lg shadow-md border border-gray-200 dark:border-neutral-700"
                >
                  <Loader2Icon className="animate-spin mb-2 text-blue-600" />
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-sm text-center text-neutral-600 dark:text-neutral-300"
                  >
                    Analyzing your resume. Please wait while our AI provides
                    feedback.
                  </motion.p>
                </motion.div>
              ))
            ) : (
              <motion.div className="flex flex-col border border-black items-center justify-center bg-neutral-100 dark:bg-neutral-800 p-6 rounded-xl h-32 max-w-[10rem] mx-auto transition-all hover:shadow-lg">
                {isDragActive ? (
                  <>
                    <IconUpload className="w-5 h-5 text-blue-500 mb-1" />
                    <p className="text-sm text-neutral-700 dark:text-neutral-200">
                      Drop it
                    </p>
                  </>
                ) : (
                  <>
                    <IconUpload className="w-6 h-6 text-neutral-500 dark:text-neutral-300" />
                  </>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>
      <Link href="/" className="flex justify-center items-center m-4">
        <Button> Back to Home</Button>
      </Link>
    </div>
  );
};

export function GridPattern() {
  const columns = 30;
  const rows = 8;
  return (
    <div className="flex bg-gray-100 dark:bg-neutral-900 shrink-0 flex-wrap justify-center items-center gap-px scale-105">
      {Array.from({ length: rows }).map((_, row) =>
        Array.from({ length: columns }).map((_, col) => {
          const index = row * columns + col;
          return (
            <div
              key={`${col}-${row}`}
              className={`w-6 h-6 rounded-[1px] ${
                index % 2 === 0
                  ? "bg-gray-50 dark:bg-neutral-950"
                  : "bg-gray-50 dark:bg-neutral-950 shadow-[0_0_1px_2px_rgba(255,255,255,0.3)_inset] dark:shadow-[0_0_1px_2px_rgba(0,0,0,0.3)_inset]"
              }`}
            />
          );
        })
      )}
    </div>
  );
}
