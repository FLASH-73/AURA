"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Assembly } from "@/lib/types";
import { api } from "@/lib/api";
import { ActionButton } from "./ActionButton";

type UploadPhase = "idle" | "dragging" | "uploading" | "error";

interface UploadDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (assembly: Assembly) => void;
}

const ACCEPTED_EXTENSIONS = [".step", ".stp"];

function isAcceptedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function UploadDialog({ open, onClose, onSuccess }: UploadDialogProps) {
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setPhase("idle");
      setErrorMessage(null);
    }
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!isAcceptedFile(file)) {
        setPhase("error");
        setErrorMessage("Only .step and .stp files are supported.");
        return;
      }
      setPhase("uploading");
      setErrorMessage(null);
      try {
        const assembly = await api.uploadCAD(file);
        onSuccess(assembly);
      } catch (err) {
        setPhase("error");
        setErrorMessage(err instanceof Error ? err.message : "Upload failed");
      }
    },
    [onSuccess],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPhase("dragging");
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPhase("idle");
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const file = e.dataTransfer.files[0];
      if (file) void handleUpload(file);
    },
    [handleUpload],
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void handleUpload(file);
    },
    [handleUpload],
  );

  if (!open) return null;

  const isDragging = phase === "dragging";
  const isUploading = phase === "uploading";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg bg-bg-primary p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[14px] font-semibold text-text-primary">
          Upload STEP File
        </h2>
        <p className="mt-1 text-[12px] text-text-secondary">
          Drop a .step or .stp file to create a new assembly.
        </p>

        {/* Dropzone */}
        <div
          className={`mt-4 flex h-40 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
            isDragging
              ? "border-accent bg-accent-light"
              : "border-bg-tertiary bg-bg-secondary"
          } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
        >
          {isUploading ? (
            <>
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-bg-tertiary border-t-accent" />
              <span className="mt-2 text-[13px] text-text-secondary">
                Parsing CAD geometry...
              </span>
            </>
          ) : (
            <>
              <svg
                className="h-8 w-8 text-text-tertiary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                />
              </svg>
              <span className="mt-2 text-[13px] text-text-secondary">
                {isDragging ? "Drop file here" : "Drop STEP file here"}
              </span>
              <span className="mt-0.5 text-[11px] text-text-tertiary">
                or click to browse
              </span>
            </>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".step,.stp"
          className="hidden"
          onChange={onFileChange}
        />

        {/* Error state */}
        {phase === "error" && errorMessage && (
          <div className="mt-3 rounded-md bg-status-error-bg px-3 py-2">
            <p className="text-[12px] text-status-error">{errorMessage}</p>
            <ActionButton
              variant="secondary"
              className="mt-2"
              onClick={() => {
                setPhase("idle");
                setErrorMessage(null);
              }}
            >
              Try Again
            </ActionButton>
          </div>
        )}

        {/* Close button */}
        {!isUploading && (
          <div className="mt-4 flex justify-end">
            <ActionButton variant="secondary" onClick={onClose}>
              Cancel
            </ActionButton>
          </div>
        )}
      </div>
    </div>
  );
}
