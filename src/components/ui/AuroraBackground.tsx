export function AuroraBackground() {
  return (
    <div className="aurora-bg fixed inset-0 z-0 pointer-events-none" aria-hidden="true">
      <div className="aurora-orb aurora-orb-green" />
      <div className="aurora-orb aurora-orb-purple" />
      <div className="aurora-orb aurora-orb-cyan" />
      <div className="aurora-vignette" />
      <div className="aurora-noise" />
    </div>
  );
}

