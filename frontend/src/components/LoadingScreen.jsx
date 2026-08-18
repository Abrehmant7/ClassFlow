function LoadingScreen({ message = "Loading..." }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="flex items-center gap-3 rounded-md border border-[#E2E8F0] bg-white px-4 py-3 text-sm text-[#475569] shadow-sm">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#2563EB] border-t-transparent" />
        <span>{message}</span>
      </div>
    </div>
  );
}

export default LoadingScreen;
