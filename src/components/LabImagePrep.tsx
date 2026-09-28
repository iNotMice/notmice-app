import React, { useEffect, useRef, useState } from 'react';

interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface LabImageCropProps {
  file: File;
  title: string;
  lead: string;
  hint: string;
  sendCrop: string;
  sendWhole: string;
  cancel: string;
  onCancel: () => void;
  onSubmit: (file: File) => void;
}

interface RedactionConfirmProps {
  previewPng: string;
  title: string;
  body: string;
  confirm: string;
  cancel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy: boolean;
}

const MIN_FRACTION = 0.12;

function clampCrop(crop: CropBox): CropBox {
  const w = Math.min(1, Math.max(MIN_FRACTION, crop.w));
  const h = Math.min(1, Math.max(MIN_FRACTION, crop.h));
  return {
    x: Math.min(1 - w, Math.max(0, crop.x)),
    y: Math.min(1 - h, Math.max(0, crop.y)),
    w,
    h,
  };
}

function edgeAt(crop: CropBox, x: number, y: number): 'n' | 's' | 'e' | 'w' | 'move' {
  const margin = 0.04;
  const nearLeft = Math.abs(x - crop.x) <= margin;
  const nearRight = Math.abs(x - (crop.x + crop.w)) <= margin;
  const nearTop = Math.abs(y - crop.y) <= margin;
  const nearBottom = Math.abs(y - (crop.y + crop.h)) <= margin;
  if (nearTop) return 'n';
  if (nearBottom) return 's';
  if (nearLeft) return 'w';
  if (nearRight) return 'e';
  return 'move';
}

async function croppedFile(file: File, image: HTMLImageElement, crop: CropBox): Promise<File> {
  const sx = Math.round(crop.x * image.naturalWidth);
  const sy = Math.round(crop.y * image.naturalHeight);
  const sw = Math.max(1, Math.round(crop.w * image.naturalWidth));
  const sh = Math.max(1, Math.round(crop.h * image.naturalHeight));
  const canvas = document.createElement('canvas');
  canvas.width = sw;
  canvas.height = sh;
  const context = canvas.getContext('2d');
  if (!context) {
    return file;
  }
  context.drawImage(image, sx, sy, sw, sh, 0, 0, sw, sh);
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, 'image/png');
  });
  if (!blob) {
    return file;
  }
  const name = file.name.replace(/\.\w+$/, '') || 'lab-crop';
  return new File([blob], `${name}.png`, { type: 'image/png' });
}

export const LabImageCrop: React.FC<LabImageCropProps> = ({
  file,
  title,
  lead,
  hint,
  sendCrop,
  sendWhole,
  cancel,
  onCancel,
  onSubmit,
}) => {
  const frameRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [url, setUrl] = useState<string>('');
  const [crop, setCrop] = useState<CropBox>({ x: 0, y: 0.16, w: 1, h: 0.84 });
  const drag = useRef<{
    edge: 'n' | 's' | 'e' | 'w' | 'move';
    start: CropBox;
    px: number;
    py: number;
  } | null>(null);

  useEffect(() => {
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width;
    const y = (event.clientY - bounds.top) / bounds.height;
    drag.current = { edge: edgeAt(crop, x, y), start: crop, px: x, py: y };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const active = drag.current;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (!active || bounds.width === 0 || bounds.height === 0) {
      return;
    }
    const x = (event.clientX - bounds.left) / bounds.width;
    const y = (event.clientY - bounds.top) / bounds.height;
    const dx = x - active.px;
    const dy = y - active.py;
    const start = active.start;
    if (active.edge === 'move') {
      setCrop(clampCrop({ ...start, x: start.x + dx, y: start.y + dy }));
      return;
    }
    if (active.edge === 'n') {
      const y0 = Math.min(start.y + start.h - MIN_FRACTION, start.y + dy);
      setCrop(clampCrop({ ...start, y: y0, h: start.y + start.h - y0 }));
      return;
    }
    if (active.edge === 's') {
      setCrop(clampCrop({ ...start, h: start.h + dy }));
      return;
    }
    if (active.edge === 'w') {
      const x0 = Math.min(start.x + start.w - MIN_FRACTION, start.x + dx);
      setCrop(clampCrop({ ...start, x: x0, w: start.x + start.w - x0 }));
      return;
    }
    setCrop(clampCrop({ ...start, w: start.w + dx }));
  };

  const onPointerUp = () => {
    drag.current = null;
  };

  const submitCrop = () => {
    const image = imageRef.current;
    if (!image) {
      onSubmit(file);
      return;
    }
    void croppedFile(file, image, crop).then(onSubmit);
  };

  return (
    <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] flex flex-col gap-4">
      <div>
        <h2 className="font-['Inter'] text-base font-bold text-[#0b1c30]">{title}</h2>
        <p className="font-['Inter'] text-xs text-[#3f4850] mt-1">{lead}</p>
      </div>
      <div
        ref={frameRef}
        className="relative overflow-hidden rounded-lg bg-[#0b1c30] self-start max-w-full touch-none"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        {url ? (
          <img
            ref={imageRef}
            src={url}
            alt=""
            className="block max-h-[60vh] max-w-full select-none"
            draggable={false}
          />
        ) : null}
        <div
          className="absolute border-2 border-[#7dd3fc] pointer-events-none"
          style={{
            left: `${crop.x * 100}%`,
            top: `${crop.y * 100}%`,
            width: `${crop.w * 100}%`,
            height: `${crop.h * 100}%`,
            boxShadow: '0 0 0 9999px rgba(11, 28, 48, 0.55)',
          }}
        />
      </div>
      <p className="font-['JetBrains_Mono'] text-[11px] text-[#565e74]">{hint}</p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={submitCrop}
          className="bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] px-4 py-2 rounded font-['Inter'] text-xs font-semibold"
        >
          {sendCrop}
        </button>
        <button
          type="button"
          onClick={() => onSubmit(file)}
          className="bg-[#ffffff] border border-[#cbd5e1] text-[#0b1c30] px-4 py-2 rounded font-['Inter'] text-xs font-semibold"
        >
          {sendWhole}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-[#565e74] px-4 py-2 font-['Inter'] text-xs"
        >
          {cancel}
        </button>
      </div>
    </div>
  );
};

export const RedactionConfirm: React.FC<RedactionConfirmProps> = ({
  previewPng,
  title,
  body,
  confirm,
  cancel,
  onConfirm,
  onCancel,
  busy,
}) => {
  return (
    <div className="bg-[#ffffff] p-5 rounded-xl border border-[#cbd5e1] flex flex-col gap-4">
      <div>
        <h2 className="font-['Inter'] text-base font-bold text-[#0b1c30]">{title}</h2>
        <p className="font-['Inter'] text-xs text-[#3f4850] mt-1">{body}</p>
      </div>
      <img
        src={`data:image/png;base64,${previewPng}`}
        alt=""
        className="max-h-[60vh] max-w-full rounded-lg border border-[#e2e8f0]"
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={busy}
          className="bg-[#006194] hover:bg-[#007bb9] text-[#ffffff] px-4 py-2 rounded font-['Inter'] text-xs font-semibold disabled:opacity-60"
        >
          {confirm}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="text-[#565e74] px-4 py-2 font-['Inter'] text-xs"
        >
          {cancel}
        </button>
      </div>
    </div>
  );
};
