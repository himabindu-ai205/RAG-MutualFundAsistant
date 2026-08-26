export function WelcomeCard() {
  return (
    <section className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
      <h2 className="font-headline-md text-headline-md-mobile md:text-headline-md text-on-surface mb-sm m-0">
        Welcome.
      </h2>
      <p className="font-body-md text-body-md text-on-surface-variant mb-0 mt-0">
        Ask questions about five SBI schemes: Large Cap, Flexicap, ELSS Tax
        Saver, Contra, and Small Cap.
      </p>
    </section>
  );
}
