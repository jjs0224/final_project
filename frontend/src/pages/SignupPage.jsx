import "./SignupPage.css";
import Modal from "../components/Modal";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import { COUNTRY_OPTIONS } from "../contents/signup";
import { GENDER } from "../contents/signup";

/* email, pw 정규식 */
const REGEX = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/,
  password: /^.{8,20}$/,
};

function validate(formData) {
  const errors = {};
  const email = formData.email.trim();
  const pw = formData.password;

  if (!email) errors.email = "Email is required.";
  else if (!REGEX.email.test(email)) errors.email = "Email must include '@' and be valid.";

  if (!pw) errors.password = "Password is required.";
  else if (!REGEX.password.test(pw)) errors.password = "Password must be 8~20 characters.";

  if (formData.password !== formData.passwordConfirm) {
    errors.passwordConfirm = "Password does not match.";
  }

  return errors;
}


function SignupPage() {

  const nav = useNavigate();

  const [formData, setformData] = useState({
    email: "",
    nickname: "",
    password: "",
    passwordConfirm: "",
    gender: "",
    country: ""
  });

  const categories = [
  {
    id: "allergy",
    label: "Allergy (Optional)",
    options: [
      { itemId: 1, label: "Peanut" },
      { itemId: 2, label: "Tree nuts" },
      { itemId: 3, label: "Milk" },
      { itemId: 4, label: "Egg" },
      { itemId: 5, label: "Wheat" },
      { itemId: 6, label: "Soy" },
      { itemId: 7, label: "Fish" },
      { itemId: 8, label: "Shellfish" },
      { itemId: 9, label: "Sesame" },
      { itemId: 10, label: "Peach" },
    ],
  },
  {
    id: "religion",
    label: "Religion (Optional)",
    options: [
      { itemId: 11, label: "Halal" },
      { itemId: 12, label: "Kosher" },
      { itemId: 13, label: "No pork" },
      { itemId: 14, label: "No beef" },
      { itemId: 15, label: "No alcohol" },
      { itemId: 16, label: "No gelatin" },
      { itemId: 17, label: "No seafood" },
      { itemId: 18, label: "No blood products" },
      { itemId: 19, label: "No animal rennet" },
      { itemId: 20, label: "Ritual restrictions" },
    ],
  },
  {
    id: "plantBased",
    label: "Plant-Based (Optional)",
    options: [
      { itemId: 21, label: "Vegan" },
      { itemId: 22, label: "Lacto" },
      { itemId: 23, label: "Ovo" },
      { itemId: 24, label: "Lacto-ovo" },
      { itemId: 25, label: "Pesco" },
      { itemId: 26, label: "Pollo" },
      { itemId: 27, label: "Flexitarian" },
      { itemId: 28, label: "No dairy" },
      { itemId: 29, label: "No egg" },
      { itemId: 30, label: "No honey" },
    ],
  },
  {
    id: "hate",
    label: "Dislike tags (Optional)",
    options: [],
  },
];

  // 카테고리 클릭 전엔 옵션이 안 나오게: 초기값을 "" 로 둠
  const [activeCategoryId, setActiveCategoryId] = useState("");

  // 카테고리별 선택값: "optionId 문자열"이 아니라 "itemId 숫자" 배열로 유지
  const [selections, setSelections] = useState(() => {
      const init = {};
      categories.forEach((c) => (init[c.id] = []));
      return init;
  });

  const activeCategory = categories.find((c) => c.id === activeCategoryId) || null;
  const checkedList = activeCategoryId ? selections[activeCategoryId] ?? [] : [];

  const onClickCategory = (categoryId) => {
      // 같은 카테고리 버튼을 다시 누르면 접히게(원치 않으면 이 if 블록 지우면 됨)
      setActiveCategoryId((prev) => (prev === categoryId ? "" : categoryId));
  };

  const toggleOption = (itemId) => {
      if (!activeCategoryId) return;

      setSelections((prev) => {
      const current = prev[activeCategoryId] ?? [];
      const exists = current.includes(itemId);

      return {
          ...prev,
          [activeCategoryId]: exists
          ? current.filter((id) => id !== itemId)
          : [...current, itemId],
      };
    });
  };

  const [nickStatus, setNickStatus] = useState("idle");
  const [nickMsg, setNickMsg] = useState("");

  const toText = (x) => {
    if (x == null) return "";
    if (typeof x === "string") return x;

    const d = x?.detail ?? x;

    if (Array.isArray(d)) {
      return d
        .map((e) => {
          const loc = Array.isArray(e.loc) ? e.loc.slice(1).join(".") : "";
          const msg = e.msg ?? JSON.stringify(e);
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("\n");
    }

    if (typeof d === "object") return JSON.stringify(d);
    return String(d);
  };

 //  input/select 공통 핸들러
  const onChange = (e) => {
    const { name, value } = e.target;
    setformData((prev) => ({ ...prev, [name]: value }));
  };

//  닉네임이 바뀌면 다시 중복확인 필요 상태로
const onNicknameChange = (e) => {
  const v = e.target.value;
  setformData((prev) => ({ ...prev, nickname: v }));

  const trimmed = v.trim();
  if (!trimmed) {
    setNickStatus("idle");
    setNickMsg("");
    return;
  }
  setNickStatus("dirty");
  setNickMsg("Please check nickname duplication.");
};

//  닉네임 중복 체크 API
const checkNickname = async () => {
  const nickname = formData.nickname.trim();
  if (!nickname) {
    setNickStatus("idle");
    setNickMsg("");
    return;
  }
  if (nickname.length < 2) {
    setNickStatus("dirty");
    setNickMsg("Nickname must be at least 2 characters.");
    return;
  }

  setNickStatus("checking");
  setNickMsg("Checking...");

  try {
    const res = await fetch(
      `/members/nickname/check?nickname=${encodeURIComponent(nickname)}`,
      { method: "GET" }
    );

    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      const available =
        data.available ??
        (typeof data.exists === "boolean" ? !data.exists : undefined) ??
        data.is_available ??
        data.ok;

      if (available === true) {
        setNickStatus("available");
        setNickMsg("Nickname is available.");
      } else if (available === false) {
        setNickStatus("taken");
        setNickMsg("Nickname already exists.");
      } else {
        setNickStatus("error");
        setNickMsg("Unexpected response from server.");
      }
      return;
    }

    if (res.status === 409) {
      setNickStatus("taken");
      setNickMsg("Nickname already exists.");
      return;
    }

    const err = await res.json().catch(() => ({}));
    setNickStatus("error");
    setNickMsg(toText(err));
  } catch (e) {
    console.error(e);
    setNickStatus("error");
    setNickMsg("Network error");
  }
};

  // payload.item_ids 생성 (중복 제거)
  const buildItemIds = () => {
    const all = Object.values(selections).flat();
    return Array.from(new Set(all));
  };

  // hate 직접 입력용
  const [hateInput, setHateInput] = useState("");
  const [hateTags, setHateTags] = useState([]); // 최대 3개

  const addHateTag = () => {
    const v = hateInput.trim();
    if (!v) return;

    // 최대 3개
    if (hateTags.length >= 3) return;

    // 중복 방지(대소문자 무시)
    const exists = hateTags.some((t) => t.toLowerCase() === v.toLowerCase());
    if (exists) {
      setHateInput("");
      return;
    }

    setHateTags((prev) => [...prev, v]);
    setHateInput("");
  };

  const removeHateTag = (tag) => {
    setHateTags((prev) => prev.filter((t) => t !== tag));
  };


  // 백엔드 POST /members 호출 
  const submitSignup = async () => {
    const errors = validate(formData);

    if (Object.keys(errors).length > 0) {
      alert(Object.values(errors).join("\n"));
      return false;
    }

    if (nickStatus !== "available") {
      alert("Please check nickname duplication first.");
      return false;
    }

    const payload = {
      email: formData.email,
      nickname: formData.nickname,
      password: formData.password,
      gender: formData.gender,
      country: formData.country,
      item_ids: buildItemIds(),
      hate_input: hateTags
    };

    console.log("SEND PAYLOAD:", payload);

    try {
      const res = await fetch("/members", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(toText(err) || `Signup failed (${res.status})`);
        return false;
      }

      const data = await res.json();
      console.log("Sign up success:", data);
      alert("Sign up complete!");
      return true;
    } catch (e) {
      console.error(e);
      alert("Network error");
      return false;
    }
  };

  //  Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState(null);

  const openModal = (type) => {
    setModalType(type);
    setIsModalOpen(true);
  };

  const handleConfirm = async () => {
    if (modalType === "cancel") {
      console.log("Cancel Complete");
      setIsModalOpen(false);
      nav("/");
      return;
    }

    // signup
    if (modalType === "signup"){
      const ok = await submitSignup();
      if (!ok) {
        setIsModalOpen(false);
        return;
      }
      
      setIsModalOpen(false);
      nav("/");
    }
  };

  return (
    <div className="signupPage">
      <Header showNav={false} showAuthArea={false}/>
        <section>
            Create your account
        </section>
        
        <section>
            <label>
            E-mail
                <input
                    name="email"
                    type="text"
                    placeholder="example@email.com"
                    maxLength={30}
                    value={formData.email}
                    onChange={onChange}
                />
            </label>

            <label>
            Nickname
                <input
                    name="nickname"
                    type="text"
                    placeholder="Please write 10 characters or less"
                    maxLength={10}
                    value={formData.nickname}
                    onChange={onNicknameChange}
                    style={{ flex: 1 }}           
                />


                {nickStatus !== "idle" && (
                  <div>
                    {nickMsg}
                  </div>
                )}
            </label>
                <button
                  type="button"
                  onClick={checkNickname}
                  disabled={nickStatus === "checking" || !formData.nickname.trim()}
                >
                 {nickStatus === "checking" ? "Checking..." : "Duplicate check"} 
                </button>

            <label>
            Password
                <input
                    name="password"
                    type="password"
                    placeholder="Not more than 8 to 20 letters"
                    maxLength={20}
                    value={formData.password}
                    onChange={onChange}                    
                />
                </label>

            <label>
            Password Check
                <input
                    name="passwordConfirm"
                    type="password"
                    placeholder="check password"
                    maxLength={20}
                    value={formData.passwordConfirm}
                    onChange={onChange}                    
                />
            </label>
  {/* 성별 선택창 */}
            <label>
            Gender
                <select name="gender" value={formData.gender} onChange={onChange}>
                    {GENDER.map((option) => {
                      return <option key={option.value} value={option.value}>
                        {option.label}
                        </option>
                    })}
                </select>
            </label>
  {/* 국가선택창 */}
            <label>
            Country
                <select name="country" value={formData.country} onChange={onChange}>
                    {COUNTRY_OPTIONS.map((option) => {
                     return <option key={option.value} value={option.value}>
                      {option.label}
                      </option>
                    })}
                </select>
            </label>

  {/* 여기부터: 카테고리 클릭 전엔 종류(체크박스) 안 보임 */}
          <section>
            <div>
              <button type="button" onClick={() => onClickCategory("allergy")}>
                Allergy (Optional) ({(selections.allergy ?? []).length})
              </button>

              <button type="button" onClick={() => onClickCategory("plantBased")}>
                Plant-based (Optional) ({(selections.plantBased ?? []).length})
              </button>
              
              <button type="button" onClick={() => onClickCategory("religion")}>
                Religion (Optional) ({(selections.religion ?? []).length})
              </button>
              
              <button type="button" onClick={() => onClickCategory("hate")}>
                Hate (Optional)
              </button>                            
            </div>

            {/* 카테고리 클릭 전엔 아무것도 안 보이게 */}
            {activeCategory ? (
              <div>
                <div>{activeCategory.label}</div>

                {/* hate 카테고리는 체크박스 대신 직접 입력 */}
                {activeCategoryId === "hate" ? (
                  <div>
                    <input
                      type="text"
                      value={hateInput}
                      placeholder="eg) coriander"
                      maxLength={50}
                      onChange={(e) => setHateInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addHateTag();
                        }
                      }}
                      disabled={hateTags.length >= 3}
                    />
                    <button
                      type="button"
                      onClick={addHateTag}
                      disabled={hateTags.length >= 3}
                    >
                      Add
                    </button>

                    {/* 태그 표시 */}
                    <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {hateTags.map((tag) => (
                        <span
                          key={tag}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "4px 8px",
                            border: "1px solid #ccc",
                            borderRadius: 999,
                            fontSize: 12,
                          }}
                        >
                          {tag}
                          <button type="button" onClick={() => removeHateTag(tag)}>
                            x
                          </button>
                        </span>
                      ))}
                    </div>

                    <div style={{ marginTop: 6, fontSize: 12 }}>
                      {hateTags.length}/3
                    </div>

                    {/* 서버로 같이 보낼 값(일단 유지용) */}
                    <input
                      type="hidden"
                      name="hateTags"
                      value={JSON.stringify(hateTags)}
                    />
                  </div>
                ) : (
                  //  기존대로 체크박스 렌더링 (hate 제외)
                  activeCategory.options.map((opt) => (
                    <label key={opt.itemId}>
                      <input
                        type="checkbox"
                        checked={checkedList.includes(opt.itemId)}
                        onChange={() => toggleOption(opt.itemId)}
                      />
                      {opt.label}
                    </label>
                  ))
                )}
              </div>
            ) : null}
          </section>
        </section>

        <section>
            <button onClick={() => openModal('cancel')}>Cancel</button>
            <button onClick={() => openModal('signup')}>Sign up</button>

            <Modal
              isOpen={isModalOpen}
              onClose={() => setIsModalOpen(false)}
              onConfirm={handleConfirm}
              message={modalType === 'cancel' ? "Are you sure you want to cancel?" : "Do you want to proceed?"}
            />
        </section>
      
    </div>
  );
}

export default SignupPage;