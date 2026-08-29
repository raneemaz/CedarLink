function VendorComingSoon({ title }) {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">{title}</h1>

      <div className="mt-6 rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
        <p className="text-gray-500">
          This screen is coming in a later update.
        </p>
      </div>
    </div>
  );
}

export default VendorComingSoon;
