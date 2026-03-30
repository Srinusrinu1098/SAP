"use client";

import Link from "next/link";

export default function Surprise() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-pink-100 p-6 text-center">
      <h1 className="text-5xl font-bold text-pink-600 mb-6">
        🎉 SRY FOR LAUGHING 😅 🎉
      </h1>
      <p className="text-gray-700 text-xl mb-6">
        You clicked too many times without uploading files! Here’s something fun
        for you 😎
      </p>
      <img
        src="/gif.gif" // put your GIF in public folder
        alt="Funny GIF"
        className="w-96 h-auto rounded-xl shadow-lg"
      />
      <p className="text-gray-600 mt-6">
        Try uploading files next time, SmartSAP will make it easy for you! 💻
      </p>
      <Link href={"/"} className=" text-[10px] p-3 rounded-xl animate-bounce ">
        Go Back
      </Link>
    </div>
  );
}
