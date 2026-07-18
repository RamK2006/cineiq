import React from 'react';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  variant?: 'text' | 'rect' | 'circle';
  style?: React.CSSProperties;
}

export default function Skeleton({
  className = '',
  width,
  height,
  borderRadius,
  variant = 'rect',
  style = {},
}: SkeletonProps) {
  const customStyle: React.CSSProperties = { ...style };

  if (width !== undefined) customStyle.width = width;
  if (height !== undefined) customStyle.height = height;

  if (borderRadius !== undefined) {
    customStyle.borderRadius = borderRadius;
  } else if (variant === 'circle') {
    customStyle.borderRadius = '50%';
  } else if (variant === 'text') {
    customStyle.borderRadius = '4px';
  } else {
    customStyle.borderRadius = '12px'; // Matches --radius-md or global style guidelines
  }

  // Set default height for text elements to prevent layout collapse
  if (variant === 'text' && !height) {
    customStyle.height = '1em';
  }

  return (
    <div
      className={`skeleton ${className}`}
      style={customStyle}
      data-testid="skeleton"
    />
  );
}
