import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  useClerk,
  useUser,
} from "@clerk/nextjs";

import ProfilePage from "../app/profile/page";

const mockedUseUser =
  useUser as jest.MockedFunction<typeof useUser>;

const mockedUseClerk =
  useClerk as jest.MockedFunction<typeof useClerk>;

describe("ProfilePage Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.mockNavigation.resetMocks();

    mockedUseUser.mockReturnValue(
      {
        isLoaded: true,
        isSignedIn: true,
        user: {
          fullName: "Jane Cinema",
          firstName: "Jane",
          lastName: "Cinema",
          imageUrl: null,
          primaryEmailAddress: {
            emailAddress: "jane@example.com",
          },
        },
      } as unknown as ReturnType<typeof useUser>,
    );

    mockedUseClerk.mockReturnValue(
      {
        openUserProfile: jest.fn(),
      } as unknown as ReturnType<typeof useClerk>,
    );
  });

  test(
    "renders authenticated Clerk user data and backend statistics",
    async () => {
      render(<ProfilePage />);

      expect(
        screen.getByText("Jane Cinema"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("jane@example.com"),
      ).toBeInTheDocument();

      await waitFor(() => {
        expect(
          screen.getByText("12"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("4"),
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText("Movies Watched"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Reviews"),
      ).toBeInTheDocument();
    },
  );

  test(
    "renders genre preferences in the taste radar",
    async () => {
      render(<ProfilePage />);

      await waitFor(() => {
        expect(
          screen.getByText(
            "Your strongest movie preference is Science Fiction.",
          ),
        ).toBeInTheDocument();
      });

      expect(
        screen.getByTestId("responsive-container"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("radar-chart"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("radar"),
      ).toBeInTheDocument();
    },
  );

  test("opens Clerk user settings", () => {
    const openUserProfile = jest.fn();

    mockedUseClerk.mockReturnValue(
      {
        openUserProfile,
      } as unknown as ReturnType<typeof useClerk>,
    );

    render(<ProfilePage />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open profile settings",
      }),
    );

    expect(openUserProfile).toHaveBeenCalledTimes(1);
  });

  test(
    "redirects signed-out users to sign-in",
    async () => {
      mockedUseUser.mockReturnValue(
        {
          isLoaded: true,
          isSignedIn: false,
          user: null,
        } as unknown as ReturnType<typeof useUser>,
      );

      render(<ProfilePage />);

      await waitFor(() => {
        expect(
          global.mockNavigation.replace,
        ).toHaveBeenCalledWith("/sign-in");
      });
    },
  );
});
