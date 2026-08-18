import { useRef, useState } from "react";
import { UploadIcon, FileIcon, CloseIcon } from "./icons";
import { formatFileSize } from "../lib/formatFileSize";

export default function Dropzone({ file, onSelect, onClear, accept = ".docx,.txt" }) {
  const inputRef = useRef(null);
  const [isDragging, setDragging] = useState(false);

  const handleFiles = (fileList) => {
    const picked = fileList?.[0];
    if (picked) onSelect(picked);
  };

  if (file) {
    return (
      <div className="sg-file-chip">
        <span className="sg-file-chip-icon">
          <FileIcon width={18} height={18} />
        </span>
        <span>
          <div className="sg-file-chip-name">{file.name}</div>
          <div className="sg-file-chip-meta">{formatFileSize(file.size)}</div>
        </span>
        <button
          type="button"
          className="sg-file-chip-remove"
          onClick={onClear}
          aria-label="Remove file"
        >
          <CloseIcon width={16} height={16} />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`sg-dropzone ${isDragging ? "is-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="sg-file-input"
        accept={accept}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <button type="button" className="sg-btn sg-btn-secondary" onClick={() => inputRef.current?.click()}>
        <UploadIcon width={16} height={16} />
        Upload document
      </button>
      <p className="sg-dropzone-hint">or drag and drop your file here</p>
      <p className="sg-dropzone-meta">DOCX, TXT · Maximum 200MB</p>
    </div>
  );
}
