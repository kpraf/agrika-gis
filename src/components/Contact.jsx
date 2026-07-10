import React, { useEffect, useState } from "react";
import Navbar from "./layout/Navbar";
import Footer from "./layout/Footer";
import ContactCTA from "./layout/ContactCTA";

const STORAGE_KEY = "agrika-gis:contact-info";

const EMPTY_FORM = { fullName: "", organization: "", phone: "", subject: "", message: "" };

export default function Contact() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saveInfo, setSaveInfo] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (saved) {
        setForm((prev) => ({ ...prev, fullName: saved.fullName || "", organization: saved.organization || "", phone: saved.phone || "" }));
        setSaveInfo(true);
      }
    } catch {
      // ignore malformed storage
    }
  }, []);

  const updateField = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const validate = () => {
    const next = {};
    if (!form.fullName.trim()) next.fullName = "Full name is required.";
    if (!form.phone.trim()) next.phone = "Phone number is required.";
    if (!form.subject.trim()) next.subject = "Subject area is required.";
    if (!form.message.trim()) next.message = "Please write a message.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    if (saveInfo) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ fullName: form.fullName, organization: form.organization, phone: form.phone })
      );
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }

    setSubmitted(true);
    setForm((prev) => ({ ...prev, subject: "", message: "" }));
  };

  return (
    <div className="w-full bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden min-h-[500px] flex flex-col">
        <div className="absolute inset-0 bg-[url('/images/farmers3.png')] bg-cover bg-center" />
        <div className="absolute inset-0 bg-[#1B3315]/30" />

        <Navbar active="Contact" />

        <div className="relative z-10 flex-1 flex flex-col items-start justify-center gap-4 px-6 md:px-12 pb-12 max-w-4xl">
          <h1 className="text-4xl md:text-6xl font-extrabold text-white leading-[1.05]">
            Contact with AgriKa-GIS
          </h1>
          <p className="text-lg md:text-xl text-[#E5E7EB] max-w-2xl">
            Fostering collaboration between research institutions, local government units, and agricultural
            communities to build sustainable, data-driven farming practices across the region.
          </p>
        </div>
      </section>

      {/* Contact Form & Image Section */}
      <section className="bg-white py-20 px-6 md:px-16 flex justify-center">
        <div className="max-w-[1280px] w-full grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
          {/* Form Column */}
          <div className="flex flex-col gap-6">
            <span className="inline-flex items-center px-4 py-1.5 rounded-full bg-[#F0FDF4] border border-[#BBF7D0] text-sm text-[#15803D] w-fit">
              Contact With Us
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-[#111827]">Send an Inquiry</h2>

            {submitted ? (
              <div className="flex flex-col gap-3 p-6 bg-[#F0FDF4] border border-[#BBF7D0] rounded-2xl">
                <h3 className="text-lg font-bold text-[#15803D]">Thanks — your message is queued.</h3>
                <p className="text-sm text-[#374151]">
                  There's no backend wired up yet to actually deliver this, but your inquiry passed validation and
                  would be sent to the AgriKA-GIS team once the contact endpoint is live.
                </p>
                <button
                  type="button"
                  onClick={() => setSubmitted(false)}
                  className="self-start px-5 py-2 rounded-full bg-[#1F6306] text-white text-sm font-semibold hover:bg-[#286A11]"
                >
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-6 pt-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <input
                      value={form.fullName}
                      onChange={updateField("fullName")}
                      placeholder="Full Name"
                      className={`px-4 py-[19px] text-base bg-white border rounded-lg outline-none focus:border-[#1F6306] ${
                        errors.fullName ? "border-red-400" : "border-[#D1D5DB]"
                      }`}
                    />
                    {errors.fullName && <span className="text-xs text-red-600">{errors.fullName}</span>}
                  </div>
                  <input
                    value={form.organization}
                    onChange={updateField("organization")}
                    placeholder="Organization / LGU"
                    className="px-4 py-[19px] text-base bg-white border border-[#D1D5DB] rounded-lg outline-none focus:border-[#1F6306]"
                  />
                  <div className="flex flex-col gap-1">
                    <input
                      value={form.phone}
                      onChange={updateField("phone")}
                      placeholder="Phone Number"
                      className={`px-4 py-[19px] text-base bg-white border rounded-lg outline-none focus:border-[#1F6306] ${
                        errors.phone ? "border-red-400" : "border-[#D1D5DB]"
                      }`}
                    />
                    {errors.phone && <span className="text-xs text-red-600">{errors.phone}</span>}
                  </div>
                  <div className="flex flex-col gap-1">
                    <input
                      value={form.subject}
                      onChange={updateField("subject")}
                      placeholder="Subject area"
                      className={`px-4 py-[19px] text-base bg-white border rounded-lg outline-none focus:border-[#1F6306] ${
                        errors.subject ? "border-red-400" : "border-[#D1D5DB]"
                      }`}
                    />
                    {errors.subject && <span className="text-xs text-red-600">{errors.subject}</span>}
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <textarea
                    value={form.message}
                    onChange={updateField("message")}
                    placeholder="Write a Message"
                    rows={6}
                    className={`px-4 py-4 text-base bg-white border rounded-lg outline-none resize-none focus:border-[#1F6306] ${
                      errors.message ? "border-red-400" : "border-[#D1D5DB]"
                    }`}
                  />
                  {errors.message && <span className="text-xs text-red-600">{errors.message}</span>}
                </div>

                <label className="flex items-center gap-2 text-sm text-[#4B5563] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={saveInfo}
                    onChange={(e) => setSaveInfo(e.target.checked)}
                    className="w-4 h-4 accent-[#1F6306]"
                  />
                  Save my info for future comments
                </label>

                <button
                  type="submit"
                  className="self-start flex items-center gap-2 px-8 py-4 rounded-full bg-[#2C6E00] text-white font-bold hover:bg-[#1F6306] transition-colors"
                >
                  Send A Message
                  <svg width="16" height="10" viewBox="0 0 16 10" fill="none">
                    <path d="M1 5h14M9 1l5 4-5 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </form>
            )}
          </div>

          {/* Image Column */}
          <img
            src="/images/farmers4.png"
            alt="AgriKA-GIS field team"
            className="w-full h-[400px] lg:h-[605px] rounded-2xl object-cover"
          />
        </div>
      </section>

      <ContactCTA />
      <Footer />
    </div>
  );
}
